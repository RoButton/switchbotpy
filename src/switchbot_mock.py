import re
from typing import List, Dict, Any, Tuple

from switchbot_timer import BaseTimer

db = {}

"""
allows to test api without an actual switchbot available. Simply change import in app.py to use this file
"""

class Scanner(object):

    def scan(self, known_dict={}):
        print("MOCK: scanner.scan()")
        switchbots = ["A1:A2:A3:A4:A5:A6", "B1:B2:B3:B4:A5:A6"]
        return switchbots

class Bot(object):

    def __init__(self, id: int, mac: str, name: str):

        if not re.match(r"[0-9A-F]{2}(?:[-:][0-9A-F]{2}){5}$", mac):
            raise ValueError("Illegal Mac Address: ", mac)

        self.id = id
        self.mac = mac
        self.name = name

        if id not in db:
            db[id] = {"id": id, 
                        "mac": mac, 
                        "name": name, 
                        "timers":[], 
                        "dual_state_mode": False,
                        "inverse_direction": False,
                        "hold_seconds":1}

    def press(self):
        print("MOCK: bot.press() -> press")

    def switch(self, on:bool):
        if on:
            print("MOCK: bot.switch() -> turn on")
        else:
            print("MOCK: bot.switch() -> turn off")

    def set_hold_time(self, sec: int):
        print("MOCK: bot.set_hold_time(sec=%d)", sec)
        db[self.id]["hold_seconds"] = sec

    def get_timer(self, idx:int) -> Tuple[BaseTimer, int]:
        print("MOCK: bot.get_timer(idx=%s)", idx)
        return db[self.id]["timers"][idx], len(db[self.id]["timers"])

    def set_timer(self, timer: BaseTimer, idx: int, num_timer: int):
        print("MOCK: bot.set_timer(timer=%s)", timer)
        assert(len(db[self.id]["timers"])==num_timer)
        db[self.id]["timers"][idx] = timer

    def set_timers(self, timers: List[BaseTimer]):
        print("MOCK: bot.set_timers(timers=%s)", timers)
        db[self.id]["timers"] = timers

    def set_current_timestamp(self):
        print("MOCK: bot.set_current_time()")
    
    def set_mode(self, dual_state: bool, inverse: bool):
        print("MOCK: bot.set_mode(dual_state=%s, inverse=%s)", dual_state, inverse)
        db[self.id]["dual_state_mode"] = dual_state
        db[self.id]["inverse_direction"] = inverse

    def get_settings(self) -> Dict[str, Any]:
        print("MOCK: bot.get_settings()")
        
        s = {} 

        s["battery"] = 99
        s["firmware"] = 4.5
        s["n_timers"] = len(db[self.id]["timers"])
        s["dual_state_mode"] = db[self.id]["dual_state_mode"]
        s["inverse_direction"] = db[self.id]["inverse_direction"]
        s["hold_seconds"] = db[self.id]["hold_seconds"]

        return s

    def get_timers(self, n_timers: int=5) -> List[BaseTimer]:
        print("MOCK: bot.get_timers(n_timers=%d)", n_timers)
        return db[self.id]["timers"]

    def encrypted(self, password: str):
        print("MOCK: bot.encrypted(password=...)")