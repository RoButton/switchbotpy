import keyring, os, getpass, secrets

from flask_bcrypt import Bcrypt

SERVICE_NAME = 'switchbot'

bcrypt = Bcrypt()

class Config(object):
    DEBUG = False

    BASE_URL = '/switchbot/api/v1'
    OPENAPI_VERSION = '3.0.2'
    JWT_TOKEN_EXPIRE_HOURS = 24

    @property
    def JWT_SECRET_KEY(self):
        key = keyring.get_password(SERVICE_NAME, 'jwt_secret_key')
        if key is None:  
            key = secrets.token_urlsafe()            
            keyring.set_password(SERVICE_NAME, 'jwt_secret_key', key)
            key = keyring.get_password(SERVICE_NAME, 'jwt_secret_key')
        return key
    
    @property
    def LOGIN_PASSWORD_HASH(self):
        pw_hash = keyring.get_password(SERVICE_NAME, 'login_password_hash')
        if pw_hash is None:
            pw = getpass.getpass(prompt='Login Password (required for receiving bearer token): ') 
            pw_hash = bcrypt.generate_password_hash(pw)
            keyring.set_password(SERVICE_NAME, 'login_password_hash', pw_hash.decode('utf-8'))
            pw_hash = keyring.get_password(SERVICE_NAME, 'login_password_hash')
        return pw_hash
    

class DevConfig(Config):
    DEBUG = True
