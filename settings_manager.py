import json
import os
from cryptography.fernet import Fernet

SETTINGS_FILE = 'aws_settings.enc'
KEY_FILE = 'secret.key'

def generate_key():
    key = Fernet.generate_key()
    with open(KEY_FILE, 'wb') as key_out:
        key_out.write(key)

def load_key():
    if not os.path.exists(KEY_FILE):
        generate_key()
    with open(KEY_FILE, 'rb') as key_in:
        return key_in.read()

def encrypt_data(data, key):
    fernet = Fernet(key)
    return fernet.encrypt(data.encode())

def decrypt_data(data, key):
    fernet = Fernet(key)
    return fernet.decrypt(data).decode()

def load_settings():
    key = load_key()
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, 'rb') as f:
            encrypted_data = f.read()
        decrypted_data = decrypt_data(encrypted_data, key)
        return json.loads(decrypted_data)
    else:
        default_settings = {
            'AWS_ACCESS_KEY_ID': '',
            'AWS_ACCESS_SECRET_KEY': '',
            'AWS_SESSION_TOKEN': '',
            'AWS_REGION': ''
        }
        save_settings(default_settings)
        return default_settings

def save_settings(settings):
    key = load_key()
    data = json.dumps(settings)
    encrypted_data = encrypt_data(data, key)
    with open(SETTINGS_FILE, 'wb') as f:
        f.write(encrypted_data)
