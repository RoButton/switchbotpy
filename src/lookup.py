from tinydb import TinyDB, Query
from configmodule import Config


db = TinyDB(Config.DB_PATH, default_table='bots')

def find_device_by_id(bot_id):
    d = db.get(doc_id=bot_id)
    if d:
        d['id'] = d.doc_id
    return d

def find_device_by_mac(mac):
    Bot = Query()
    d = db.get(Bot.mac == mac)
    if d:
        d['id'] = d.doc_id
    return d

def find_devices_by_name(name):
    Bot = Query()
    ds = db.search(Bot.name == name)
    if ds:
        for d in ds:
            d['id'] = d.doc_id
    return ds

def insert_device(mac, name=None):
    if name is None:
        name = "Unknown"

    # ensure MAC ID is unqiue
    Bot = Query()
    if db.contains(Bot.mac == mac):
        raise ValueError("Cannot Insert Device, because it is already in db!")

    bot = {'mac': mac, 'name':name}
    device_id = db.insert(bot)

    bot['id'] = device_id

    return device_id

def delete_device(bot_id):
    db.remove(doc_ids=[bot_id])

def set_device_name(bot_id, name):
    db.update({'name': name}, doc_ids=[bot_id])
    