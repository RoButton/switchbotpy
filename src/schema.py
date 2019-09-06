import marshmallow as ma


class BotListSchema(ma.Schema):
    class Meta:
        strict = True
        ordered = True

    id = ma.fields.Int(dump_only=True)      # read-only
    mac = ma.fields.String(dump_only=True)  # read-only
    name = ma.fields.String(dump_only=True) # read-only


class BotSchema(ma.Schema):

    class Meta:
        strict = True
        ordered = True

    id = ma.fields.Int(dump_only=True) # read-only
    mac = ma.fields.String(dump_only=True)  # read-only
    name = ma.fields.String()
    password = ma.fields.String(load_only=True) # write-only

    firmware = ma.fields.Decimal(places=1, dump_only=True, as_string=True) # read-only
    battery = ma.fields.Int(dump_only=True, validate=ma.validate.Range(min=0, max=99)) # read-only
    n_timers = ma.fields.Int(dump_only=True, validate=ma.validate.Range(min=0, max=5)) # read-only

    hold_seconds = ma.fields.Int(validate=ma.validate.Range(min=0, max=60))
    dual_state_mode = ma.fields.Bool()
    inverse_direction = ma.fields.Bool()


class TimerSchema(ma.Schema):
    class Meta:
        strict = True
        ordered = True
    
    id = ma.fields.Int(dump_only=True) 
    mode = ma.fields.String(dump_only=True, validate=ma.validate.OneOf(choices=["standard", "interval"])) # read-only
    
    action = ma.fields.String(validate=ma.validate.OneOf(choices=["press", "turn_on", "turn_off"]), required=True)
    enabled = ma.fields.Bool(required=True)
    weekdays = ma.fields.List(ma.fields.Int(validate=ma.validate.Range(min=1, max=7)), validate=ma.validate.Length(min=0, max=7), required=True)
    hour = ma.fields.Int(validate=ma.validate.Range(min=0, max=23), required=True)
    min = ma.fields.Int(validate=ma.validate.Range(min=0, max=59), required=True)

class ActionSchema(ma.Schema):
    class Meta:
        strict = True
        ordered = True

    action = ma.fields.String(load_only=True, validate=ma.validate.OneOf(choices=["press", "turn_on", "turn_off"]), required=True)

class LoginSchema(ma.Schema):
    class Meta:
        strict = True
        ordered = True
    
    name = ma.fields.String(required=True)
    password = ma.fields.String(required=True, load_only=True)
    token = ma.fields.String(dump_only=True)