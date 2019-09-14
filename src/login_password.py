import keyring, getpass
from flask_bcrypt import Bcrypt

"""
utility script to set the password required to receive a bearer token
"""

bcrypt = Bcrypt()
SERVICE_NAME = 'switchbot'

pw = getpass.getpass(prompt='Login Password (required for receiving bearer token): ') 
pw_hash = bcrypt.generate_password_hash(pw)
keyring.set_password(SERVICE_NAME, 'login_password_hash', pw_hash.decode('utf-8'))

print("Login Password Changed! Don't forget to restart webserver (e.g. Gunicorn) for changes to become active.")