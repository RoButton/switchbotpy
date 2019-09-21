from datetime import timedelta
from typing import Any, Dict, List

import keyring, logging
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
from schema import ActionSchema, BotListSchema, BotSchema, LoginSchema, TimerSchema, PatchTimerSchema
from switchbot import Bot, Scanner
from switchbot import LOG as SwitchbotLog
from switchbot_timer import Action, StandardTimer
from switchbot_util import ActionStatus, SwitchbotError

app = Flask('switchbot_api')
app.config.from_object(Config())

bcrypt = Bcrypt(app)
api = Api(app)
api.spec.components.security_scheme('bearerAuth', {'type': 'http', 'scheme': 'bearer', 'bearerFormat': 'JWT'})

jwt = JWTManager(app)
app.wsgi_app = ProxyFix(app.wsgi_app, num_proxies=1)
limiter = Limiter(app, key_func=get_remote_address)
LOG = create_logger(app)

gunicorn_logger = logging.getLogger('gunicorn.error')
logging.getLogger('switchbot').setLevel(gunicorn_logger.level)
LOG.setLevel(gunicorn_logger.level)

def connect(bot_id: int):
    LOG.debug("connect to bot: %s", bot_id)

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
    @blbs.response(BotListSchema(many=True), description="A list of switchbots")
    @blbs.doc(security=[{"bearerAuth":[]}])
    def get(self):
        """List available switchbots
        
        Return all switchbots within BLE range
        """

        bots = []
        scanner = Scanner()

        addresses = scanner.scan(known_dict={})
        LOG.debug("addresses: %s", str(addresses))

        for address in addresses:
            bot = lookup.find_device_by_mac(mac=address)
            if bot is None: # new bot
                LOG.debug("insert new bot: %s", address)
                bot_id = lookup.insert_device(mac=address)
                bot = lookup.find_device_by_id(bot_id)
            
            bots.append(bot)

        return bots


blb = Blueprint(
    'bot', 'bot', url_prefix=app.config['BASE_URL'] + '/bot',
    description='Operations on a bot'
)

@blb.route('/<int:bot_id>')
class BotAPI(MethodView):

    @jwt_required
    @blb.response(BotSchema, description="A switchbot")
    @blb.doc(security=[{"bearerAuth":[]}])
    def get(self, bot_id: int):
        """Find bot settings by id

        Return bot settings based on id, obtained via communicating to the bot via BLE.
        """
        bot = connect(bot_id=bot_id)

        # communicate with bot to get settings
        try:
            d = bot.get_settings()
        except SwitchbotError as e:
            handle_switchbot_error(e)

        d["id"] = bot.id
        d["mac"] = bot.mac
        d["name"] = bot.name

        LOG.debug("bot settings: %s", d)
        
        return d

    @jwt_required
    @blb.arguments(BotSchema)
    @blb.response(BotSchema, description="An updated switchbot")
    @blb.doc(security=[{"bearerAuth":[]}])
    def patch(self, update_data: Dict[str, Any], bot_id: int):
        """Update bot settings by id

        Update bot settings (password, device name, hold time, mode) by id
        (password not set on switchbot but instead this password is only
        used for the encrypted communication with the bot)
        """
        
        LOG.debug("update data: %s", update_data)

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
            LOG.debug("updated bot settings: %s", d)

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
    @blts.response(TimerSchema(many=True), description="A list of timers")
    @blts.doc(security=[{"bearerAuth":[]}])
    def get(self, bot_id: int):
        """List all timers of a bot based on id

        Return timers of a bot based on id
        """
        bot = connect(bot_id=bot_id)
        result = []
        try:
            timers = bot.get_timers()
        except SwitchbotError as e:
            handle_switchbot_error(e)

        for i, timer in enumerate(timers):
            t = timer.to_dict(timer_id=i)
            LOG.debug("timer %d: %s", i, t)
            result.append(t)
        return result

    @jwt_required
    @blts.arguments(TimerSchema)
    @blts.response(TimerSchema, code=201, description="A timer created")
    @blts.doc(security=[{"bearerAuth":[]}])
    def post(self, new_data: Dict[str, Any], bot_id: int):
        """Add timer to a bot based on id
        
        Provide timer data to create a new timer for a bot identified by id.
        """
        LOG.debug("new data: %s", new_data)

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
        LOG.debug("new timer: %s", t)
        return t


    @jwt_required
    @blts.arguments(PatchTimerSchema(many=True))
    @blts.response(TimerSchema(many=True), description="Timers updated")
    @blts.doc(security=[{"bearerAuth":[]}])
    def patch(self, update_data: List[Dict[str, Any]], bot_id: int):
        """Update multiple timers of bot by id
        
        Provide TODO [nku]
        """
        LOG.debug("new data: %s", str(update_data))

        # TODO [nku] loop over update data, get the timer by id of update data, update the fields and set timer

blta = Blueprint(
    'timer', 'timer', url_prefix= app.config['BASE_URL'] + '/bot/<int:bot_id>/timer',
    description='Operations on a timer'
)

@blta.route('/<int:timer_id>')
class TimerAPI(MethodView):

    @jwt_required
    @blta.arguments(TimerSchema(partial=True))
    @blta.response(TimerSchema, description="A timer")
    @blta.doc(security=[{"bearerAuth":[]}])
    def patch(self, update_data: Dict[str, Any], bot_id: int, timer_id: int):
        """Update a timer by id of a bot identified by id
        
        Provide timer data to update a new timer of a bot identified by id.
        """
        LOG.debug("timer update data: %s", update_data)
        
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
        LOG.debug("updated timer: %s", t)
        return t

    @jwt_required
    @blta.response(code=204, description="OK")
    @blta.doc(security=[{"bearerAuth":[]}])
    def delete(self, bot_id: int, timer_id: int):
        """Delete a timer by id of a bot identified by id
        
        Delete a timer by id of a bot identified by id
        """

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
    @blas.response(code=204, description="OK")
    @blas.doc(security=[{"bearerAuth":[]}])
    def post(self, new_data: Dict[str, Any], bot_id: int):
        """Perform an Action (Press, Turn On, Turn Off) on a bot by id
        
        Perform an Action (Press, Turn On, Turn Off) on a bot identified by id.
        """

        bot = connect(bot_id=bot_id)
        try: 
            if new_data['action'] == "press":
                bot.press()
                LOG.info("bot pressed")
            elif new_data['action'] == "turn_on":
                bot.switch(on=True)
                LOG.info("bot turned on")
            elif new_data['action'] == "turn_off":
                bot.switch(on=False)
                LOG.info("bot turned off")
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
    @bll.response(LoginSchema, code=201, description="token created")
    def post(self, new_data: Dict[str, Any]):
        """Obtain bearer token

        Obtain a bearer token by providing a valid login password
        """

        LOG.info("login of remote address: %s", str(get_remote_address()))

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
