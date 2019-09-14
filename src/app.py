from datetime import timedelta
from typing import Any, Dict

import keyring
from flask import Flask
from flask.logging import create_logger
from flask.views import MethodView
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager, create_access_token, jwt_required
from flask_rest_api import Api, Blueprint, abort
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.contrib.fixers import ProxyFix

import lookup
from configmodule import Config
from schema import ActionSchema, BotListSchema, BotSchema, LoginSchema, TimerSchema
from switchbot import Bot, Scanner
from switchbot_timer import Action, StandardTimer
from switchbot_util import ActionStatus, SwitchbotError

app = Flask('Switchbot')
app.config.from_object(Config())

bcrypt = Bcrypt(app)
api = Api(app)
jwt = JWTManager(app)
app.wsgi_app = ProxyFix(app.wsgi_app, num_proxies=1)
limiter = Limiter(app, key_func=get_remote_address)
LOG = create_logger(app)

def connect(bot_id: int):
    print("Connect to Bot: %s", bot_id)
    # find mac address in db
    device = lookup.find_device_by_id(bot_id=bot_id)

    if device is None:
        LOG.warning("bot not found: %s", bot_id)
        abort(404, message="bot not found")

    # create bot
    bot = Bot(id=device['id'], mac=device['mac'], name=device['name'])

    pw = keyring.get_password('switchbot', device['mac'])
    if pw is None:
        abort(403, message="missing bot password")

    bot.encrypted(pw)
    return bot

def handle_switchbot_error(error: SwitchbotError):
    if error.switchbot_action_status == ActionStatus.wrong_password:
        abort(403, message="wrong or missing bot password")
    else:
        abort(503, message=str(error) + ": please retry")


blbs = Blueprint(
    'bots', 'bots', url_prefix=app.config['BASE_URL'] + '/bots',
    description='Operations on bots'
)

@blbs.route('')
class BotListAPI(MethodView):

    @jwt_required
    @blbs.response(BotListSchema(many=True))
    def get(self):
        """
        list available switchbots
        """
        LOG.info("GET: bots")

        bots = []
        scanner = Scanner()

        addresses = scanner.scan(known_dict={})
        LOG.debug("addresses: %s", str(addresses))

        for address in addresses:
            bot = lookup.find_device_by_mac(mac=address)
            if bot is None: # new bot
                LOG.debug("insert new bot: %s", address)
                bot = lookup.insert_device(mac=address)
            
            bots.append(bot)

        return bots


blb = Blueprint(
    'bot', 'bot', url_prefix=app.config['BASE_URL'] + '/bot',
    description='Operations on a bot'
)

@blb.route('/<int:bot_id>')
class BotAPI(MethodView):

    @jwt_required
    @blb.response(BotSchema)
    def get(self, bot_id: int):
        
        LOG.info("GET: bot %d", bot_id)
        bot = connect(bot_id=bot_id)

        # communicate with bot to get settings
        try:
            d = bot.get_settings()
        except SwitchbotError as e:
            handle_switchbot_error(e)


        LOG.debug("bot settings: %s", d)

        d["id"] = bot.id
        d["mac"] = bot.mac
        d["name"] = bot.name
        
        return d

    @jwt_required
    @blb.arguments(BotSchema)
    @blb.response(BotSchema)
    def put(self, update_data: Dict[str, Any], bot_id: int):
        
        LOG.info("PUT: bot %d", bot_id)
        LOG.debug(" data: %s", update_data)

        if 'password' in update_data:
            device = lookup.find_device_by_id(bot_id=bot_id)
            keyring.set_password('switchbot', device['mac'], update_data['password'])
        
        bot = connect(bot_id=bot_id)

        try:
            if 'name' in update_data:
                lookup.set_device_name(bot_id=bot_id, name=update_data['name'])

            if 'hold_seconds' in update_data:
                bot.set_hold_time(sec= update_data['hold_seconds'])
            
            if ('dual_state_mode' in update_data) or ('inverse_direction' in update_data):
                
                if not ('dual_state_mode' in update_data and 'inverse_direction' in update_data): 
                    # if not both are set, need to query the bot for the current setting
                    d = self.get(bot_id=bot_id)
                    dual_state = d["dual_state_mode"]
                    inverse_direction = d["inverse_direction"]
                
                if 'dual_state_mode' in update_data:
                    dual_state = update_data['dual_state_mode']

                if 'inverse_direction' in update_data:
                    inverse_direction = update_data['inverse_direction']
            
                bot.set_mode(dual_state=dual_state, inverse=inverse_direction)

            
            d  = self.get(bot_id=bot_id)

        except SwitchbotError as e:
            handle_switchbot_error(e)
        
        return d


blts = Blueprint(
    'timers', 'timers', url_prefix=app.config['BASE_URL'] + '/bot/<int:bot_id>/timers',
    description='Operations on timers'
)

@blts.route('')
class TimerListAPI(MethodView):

    @jwt_required
    @blts.response(TimerSchema(many=True))
    def get(self, bot_id: int):
        bot = connect(bot_id=bot_id)
        result = []
        try:
            timers = bot.get_timers()
        except SwitchbotError as e:
            handle_switchbot_error(e)

        for i, timer in enumerate(timers):
            t = timer.to_dict(timer_id=i)
            result.append(t)
        return result

    @jwt_required
    @blts.arguments(TimerSchema)
    @blts.response(TimerSchema, code=201)
    def post(self, new_data: Dict[str, Any], bot_id: int):
        """Add a new timer"""
        LOG.debug(" data: %s", new_data)

        bot = connect(bot_id=bot_id)
        try:
            timers = bot.get_timers()
        
            n_timer = len(timers)

            if n_timer >= 5:
                abort(400, message="no support for more than 5 timers")

            timer = StandardTimer(action=Action[new_data["action"]],
                                    enabled=new_data["enabled"], 
                                    weekdays=new_data["weekdays"],
                                    hour=new_data["hour"],
                                    min=new_data["min"])

            timers.append(timer)
            bot.set_timers(timers)

        except SwitchbotError as e:
            handle_switchbot_error(e)

        t = timer.to_dict(timer_id=n_timer)
        return t

blta = Blueprint(
    'timer', 'timer', url_prefix= app.config['BASE_URL'] + '/bot/<int:bot_id>/timer',
    description='Operations on a timer'
)

@blta.route('/<int:timer_id>')
class TimerAPI(MethodView):

    @jwt_required
    @blta.arguments(TimerSchema(partial=True))
    @blta.response(TimerSchema)
    def put(self, update_data: Dict[str, Any], bot_id: int, timer_id: int):
        """
        update timer of a bot
        """
        LOG.debug(" data: %s", update_data)
        
        if timer_id < 0 or timer_id > 4:
            abort(404, message="timer not found")

        bot = connect(bot_id=bot_id)

        try:
            timer, num_timer = bot.get_timer(idx=timer_id)

            if timer is None:
                abort(404, message="timer not found")
            
            data = timer.to_dict()

            for field in ["action", "enabled", "weekdays", "hour", "min"]:
                if field in update_data:
                    data[field] = update_data[field]
                
            timer_updated = StandardTimer(action=Action[data["action"]],
                                    enabled=data["enabled"], 
                                    weekdays=data["weekdays"],
                                    hour=data["hour"],
                                    min=data["min"])

            bot.set_timer(timer_updated, idx=timer_id, num_timer=num_timer)

        except SwitchbotError as e:
            handle_switchbot_error(e)

        t = timer_updated.to_dict(timer_id=timer_id)
        return t

    @jwt_required
    @blta.response(code=204)
    def delete(self, bot_id: int, timer_id: int):
        """Delete timer of bot"""

        bot = connect(bot_id=bot_id)

        try: 
            timers = bot.get_timers()

            if timer_id >= len(timers):
                abort(404, message="timer not found")
            
            del timers[timer_id]

            bot.set_timers(timers)

        except SwitchbotError as e:
            handle_switchbot_error(e)


blas = Blueprint(
    'actions', 'actions', url_prefix=app.config['BASE_URL'] + '/bot/<int:bot_id>/actions',
    description='Operations on actions'
)

@blas.route('')
class ActionListAPI(MethodView):

    @jwt_required
    @blas.arguments(ActionSchema)
    @blas.response(code=204)
    def post(self, new_data: Dict[str, Any], bot_id: int):
        """Perform an Action"""
        bot = connect(bot_id=bot_id)
        try: 
            if new_data['action'] == "press":
                bot.press()
            elif new_data['action'] == "turn_on":
                bot.switch(on=True)
            elif new_data['action'] == "turn_off":
                bot.switch(on=False)
            else:
                abort(400, message="unknown action")
        except SwitchbotError as e:
            handle_switchbot_error(e)

bll = Blueprint(
    'login', 'login', url_prefix=app.config['BASE_URL'] + '/login',
    description='Login'
)

@bll.route('')
class LoginAPI(MethodView):

    decorators = [limiter.limit(app.config['LOGIN_LIMITER_LIMIT'])]

    @bll.arguments(LoginSchema)
    @bll.response(LoginSchema, code=201)
    def post(self, new_data: Dict[str, Any]):
        """Perform a Login"""

        LOG.warning("Get Remote Address: " +  str(get_remote_address()))

        candidate = new_data['password']

        if not bcrypt.check_password_hash(app.config['LOGIN_PASSWORD_HASH'], candidate):
            abort(400, message='Password is incorrect.')

        access_token = create_access_token(identity=new_data['name'], expires_delta=timedelta(hours=app.config['JWT_TOKEN_EXPIRE_HOURS']))

        return {'name': new_data['name'], 'token': access_token}


api.register_blueprint(blbs)
api.register_blueprint(blb)
api.register_blueprint(blts)
api.register_blueprint(blta)
api.register_blueprint(blas)
api.register_blueprint(bll)
