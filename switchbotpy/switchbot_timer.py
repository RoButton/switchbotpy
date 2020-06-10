from enum import Enum
from abc import ABC
from typing import List


def parse_timer_cmd(val: bytes):

    num_timer = val[1]
    weekdays = _from_byte_to_iso_weekdays(val[3])
    hour = val[4]
    minutes = val[5]

    interval_mode = val[6] & 15 # 15 = 00001111 in binary and interval mode is only in second part of the byte
    action = val[7] & 15 # action mode is only in second part of the byte
    interval_timer_sum = val[8]
    interval_hour = val[9]
    interval_min = val[10]

    enabled = val[3] != 0

    if not enabled:
        # if a timer is disabled, then the repeating pattern is stored in the first part of the interval mode and the action mode
        repeat = (val[6] & 240) | ((val[7] & 240) >> 4)
        weekdays = _from_byte_to_iso_weekdays(repeat)

    if not enabled and hour == 0 and minutes == 0 and interval_timer_sum == 0 and interval_hour == 0 and interval_min == 0:
        timer = None # timer not set
    elif interval_mode:
        timer = IntervalTimer(enabled=enabled, 
                                mode=interval_mode, 
                                action=Action(action), 
                                timer_sum=interval_timer_sum,
                                hour=interval_hour,
                                min=interval_min)
    else:
        timer = StandardTimer(enabled=enabled, weekdays=weekdays, hour=hour, min=minutes, action=Action(action))

    return timer, num_timer

def delete_timer_cmd(idx: int, num_timer: int):

    # \x03 for 0'th timer, \x13 for 1st timer, \x23 for 2nd timer
    cmd = _to_byte(idx*16+3)

    # \x01 for 1 timer, \x02 for 2 timers, ... , \x05 for 5 timers
    cmd += _to_byte(num_timer)

    # filler repeat hour min mode action interval_timer_sum interval_hour interval_min
    cmd += b'\x00\x00\x00\x00\x00\x00\x00\x00\x00'

    return cmd

   

def _to_byte(value: int):
    return value.to_bytes(1, byteorder='big')

def _from_iso_weekdays_to_byte(weekdays: List[int]):
    
    val = 0
    for day in weekdays:
        val += 2 ** (day-1)

    if val == 0:
        val = 128
        
    return _to_byte(val)

def _from_byte_to_iso_weekdays(val: bytes):
    weekdays = []
    if val & 1:  weekdays += [1] # Monday
    if val & 2:  weekdays += [2] # Tuesday
    if val & 4:  weekdays += [3] # Wednesday
    if val & 8:  weekdays += [4] # Thursday
    if val & 16: weekdays += [5] # Friday
    if val & 32: weekdays += [6] # Saturday
    if val & 64: weekdays += [7] # Sunday
    # if val & 128: no repeat

    return weekdays

class Action(Enum):
    press = 0
    turn_on = 1
    turn_off = 2

class Mode(Enum):
    standard = 0
    interval = 1 # TODO [nku] not sure, needs to be verified


class BaseTimer(ABC):  

    def __init__(self, enabled:bool=None, weekdays:List[int]=None, hour:int=None, min:int=None, mode:Mode=None, action:Action=None, interval_timer_sum:int=None, interval_hour:int=None, interval_min:int=None):
        self.enabled = enabled 
        self.weekdays = weekdays
        self.hour = hour if hour else 0
        self.min = min if min else 0
        self.mode = mode
        self.action = action
        self.interval_timer_sum = interval_timer_sum if interval_timer_sum else 0
        self.interval_hour = interval_hour if interval_hour else 0
        self.interval_min = interval_min if interval_min else 0

        super().__init__()


    def to_cmd(self, idx: int, num_timer: int):

        if idx < 0 or idx >= num_timer or num_timer > 5:
            raise ValueError("Illegal Argument: Support for max 5 timers and idx must be < num_timer")

        # \x03 for 0'th timer, \x13 for 1st timer, \x23 for 2nd timer
        cmd = _to_byte(idx*16+3)

        # \x01 for 1 timer, \x02 for 2 timers, ... , \x05 for 5 timers
        cmd += _to_byte(num_timer)

        # filler
        cmd += b'\x00'

        # byte[0] = No Repeat, byte[1] = Sunday, byte[2] = Saturday, ... byte[7] = Monday
        repeat = _from_iso_weekdays_to_byte(self.weekdays)
        if self.enabled:
            cmd += repeat
        else: 
            cmd += b'\x00'

        cmd += _to_byte(self.hour)
        cmd += _to_byte(self.min)
        
        mode_b = _to_byte(self.mode.value)
        if not self.enabled:
             # if timer is not enabled, store the first 4 bits (no_rep, sun, sat, fri)
             # of the repeating pattern in the top 4 bits of the action
            mode_b = _to_byte(ord(mode_b) | (ord(repeat) & 240))
            
        cmd += mode_b

        action_b = _to_byte(self.action.value)
        if not self.enabled:
            # if timer is not enabled, store the last 4 bits (mon, tue, wed, thu)
            # of the repeating pattern in the top 4 bits of the action
            action_b = _to_byte(ord(action_b) | ((ord(repeat) & 15) << 4))
            
        cmd += action_b

        cmd += _to_byte(self.interval_timer_sum)
        cmd += _to_byte(self.interval_hour)
        cmd += _to_byte(self.interval_min)

        return cmd

    def to_dict(self, timer_id=None):
        raise NotImplementedError()
        


class StandardTimer(BaseTimer):

    def __init__(self, enabled: bool, weekdays: List[int], hour: int, min: int, action: Action):
        BaseTimer.__init__(self, mode=Mode.standard, action=action, enabled=enabled, weekdays=weekdays, hour=hour, min=min)

    def to_dict(self, timer_id=None):
        d = {}
        if timer_id is not None:
            d['id'] = timer_id
        d['mode'] = self.mode.name
        d['action'] = self.action.name
        d['enabled'] = self.enabled
        d['weekdays'] = self.weekdays
        d['hour'] = self.hour
        d['min'] = self.min
        return d


class IntervalTimer(BaseTimer):
    def __init__(self, enabled: bool, mode: Mode, action: Action, timer_sum: int, hour: int, min: int):
        BaseTimer.__init__(self, enabled=enabled, mode=mode, action=action, interval_timer_sum=timer_sum, interval_hour=hour, interval_min=min)
    
    def to_dict(self, timer_id=None):
        d = {}
        if timer_id is not None:
            d['id'] = timer_id
        d['mode'] = self.mode.name
        d['action'] = self.action.name
        d['enabled'] = self.enabled
        d['timer_sum'] = self.interval_timer_sum
        d['hour'] = self.interval_hour
        d['min'] = self.interval_min
        return d