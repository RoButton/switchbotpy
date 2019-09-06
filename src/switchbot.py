import logging
import re
import time
import zlib
from binascii import hexlify
from typing import Any, Dict, List, Tuple
from uuid import UUID

import pygatt
from switchbot_timer import BaseTimer, delete_timer_cmd, parse_timer_cmd
from switchbot_util import ActionStatus, SwitchbotError, handle_notification, notification_queue

# TODO [nku] add logging
LOG = logging.getLogger(__name__)

class Scanner(object):
    def __init__(self):
        self.adapter = pygatt.GATTToolBackend()

    def scan(self, known_dict=dict()) -> List[str]:
        try:
            self.adapter.start()
            devices = self.adapter.scan()
        finally:
            self.adapter.stop()

        switchbots = []

        for device in devices:    
            if device['address'] in known_dict:
                # mac of device is known -> don't need to check characteristics to know if device is a switchbot
                if known_dict[device['address']]:
                    switchbots.append(device['address'])
            elif self._is_switchbot(mac=device['address']):
                 # mac of device is unknown -> check characteristics to know if device is a switchbot
                switchbots.append(device['address'])
    
        return switchbots

    def _is_switchbot(self, mac: str) -> bool:
        try:
            self.adapter.start()
            device = self.adapter.connect(mac, address_type=pygatt.BLEAddressType.random)
            characteristics = self.adapter.discover_characteristics(device)
            device.disconnect()

            is_switchbot = UUID("{cba20002-224d-11e6-9fb8-0002a5d5c51b}") in characteristics.keys() and UUID("{cba20003-224d-11e6-9fb8-0002a5d5c51b}") in characteristics.keys()
        
        except pygatt.exceptions.NotConnectedError:
            # e.g. if device uses different addressing
            is_switchbot = False
        
        finally:
            self.adapter.stop()

        return is_switchbot


class Bot(object):

    def __init__(self, id: int, mac: str, name: str):

        if not re.match(r"[0-9A-F]{2}(?:[-:][0-9A-F]{2}){5}$", mac):
            raise ValueError("Illegal Mac Address: ", mac)

        self.id = id
        self.mac = mac
        self.name = name

        self.adapter = pygatt.GATTToolBackend()
        self.device = None
        self.pw = None
        self.notification_activated = False

    def press(self):
        
        try:
            self.adapter.start()
            self._connect()
            self._activate_notifications()

            if self.pw:
                cmd = b'\x57\x11' + self.pw
            else:
                cmd = b'\x57\x01'

            value = self._write_cmd_and_wait_for_notification(handle=0x16, cmd=cmd)
            self._handle_switchbot_status_msg(value=value)

        finally:
            self.adapter.stop()


    def switch(self, on: bool):
        try:
            self.adapter.start()
            self._connect()
            self._activate_notifications()

            if self.pw:
                cmd = b'\x57\x11' + self.pw
            else:
                cmd = b'\x57\x01'

            if on:
                cmd += b'\x01'
            else: # off
                cmd += b'\x02'

            value = self._write_cmd_and_wait_for_notification(handle=0x16, cmd=cmd)
            self._handle_switchbot_status_msg(value=value)

        finally:
            self.adapter.stop()


    def set_hold_time(self, sec: int):

        if sec < 1 or sec > 60:
            raise ValueError("hold time must be between [1, 60] seconds")

        try:
            self.adapter.start()
            self._connect()
            self._activate_notifications()

            if self.pw:
                cmd = b'\x57\x1f' + self.pw
            else:
                cmd = b'\x57\x0f'

            cmd += b'\x08' + sec.to_bytes(1, byteorder='big')

            value = self._write_cmd_and_wait_for_notification(handle=0x16, cmd=cmd)
            self._handle_switchbot_status_msg(value=value)

        finally:
            self.adapter.stop()

    def get_timer(self, idx:int) -> Tuple[BaseTimer, int]:

        try:
            self.adapter.start()
            self._connect()
            self._activate_notifications()

            if self.pw:
                cmd = b'\x57\x18' + self.pw
            else:
                cmd = b'\x57\x08'

            timer_id = (idx * 16 + 3).to_bytes(1, byteorder='big')
            cmd += timer_id

            # trigger and wait for notification
            value = self._write_cmd_and_wait_for_notification(handle=0x16, cmd=cmd)
            self._handle_switchbot_status_msg(value=value)

            # parse result
            timer, num_timer = parse_timer_cmd(value)

        finally:
            self.adapter.stop()

        return timer, num_timer

    def set_timer(self, timer: BaseTimer, idx: int, num_timer: int):

        if idx < 0 or idx > 4 or num_timer <= idx or num_timer < 1 or num_timer > 5:
            raise ValueError("Illegal Timer Idx or Number of Timers")
    
        try:
            self.adapter.start()
            self._connect()
            self._activate_notifications()

            if self.pw:
                cmd = b'\x57\x19' + self.pw
            else:
                cmd = b'\x57\x09'

            cmd += timer.to_cmd(idx=idx, num_timer=num_timer)
            value = self._write_cmd_and_wait_for_notification(handle=0x16, cmd=cmd)
            self._handle_switchbot_status_msg(value=value)

        finally:
            self.adapter.stop()


    def set_timers(self, timers: List[BaseTimer]):

        try:
            self.adapter.start()
            self._connect()
            self._activate_notifications()

            if self.pw:
                cmd_base = b'\x57\x19' + self.pw
            else:
                cmd_base = b'\x57\x09'

            num_timer = len(timers)
            for i, timer in enumerate(timers):      
                cmd = cmd_base
                cmd += timer.to_cmd(idx=i, num_timer=num_timer)
                value = self._write_cmd_and_wait_for_notification(handle=0x16, cmd=cmd)
                self._handle_switchbot_status_msg(value=value)
            
            for i in range(num_timer, 5):
                cmd = cmd_base
                cmd += delete_timer_cmd(idx=i, num_timer=num_timer)
                value = self._write_cmd_and_wait_for_notification(handle=0x16, cmd=cmd)
                self._handle_switchbot_status_msg(value=value)

        
        finally:
            self.adapter.stop()


    def set_current_timestamp(self):

        try:
            self.adapter.start()
            self._connect()
            self._activate_notifications()

            if self.pw:
                cmd_base = b'\x57\x19' + self.pw
            else:
                cmd_base = b'\x57\x09'

            time_sec_utc = time.time()
            time_local = time.localtime(time_sec_utc)
            offset = time_local.tm_gmtoff
            timestamp = int(time_sec_utc + offset)

            cmd = cmd_base + b'\x01'
            cmd  += timestamp.to_bytes(8, byteorder='big')

            value = self._write_cmd_and_wait_for_notification(handle=0x16, cmd=cmd)
            self._handle_switchbot_status_msg(value=value)

        finally:
            self.adapter.stop()
    

    def set_mode(self, dual_state: bool, inverse: bool):

        try:
            self.adapter.start()
            self._connect()
            self._activate_notifications()

            # delete all timers -> because if dual_state changes, then also action of timer needs to change
            self.set_timers(timers=[])

            if self.pw:
                cmd_base = b'\x57\x13' + self.pw
            else:
                cmd_base = b'\x57\x03'

            cmd = cmd_base + b'\x64'

            config = 0
            if dual_state:
                config += 16
            if inverse:
                config += 1

            cmd += config.to_bytes(1, byteorder='big')

            value = self._write_cmd_and_wait_for_notification(handle=0x16, cmd=cmd)
            self._handle_switchbot_status_msg(value=value)

        finally:
            self.adapter.stop()

    def get_settings(self) -> Dict[str, Any]:
        try:
            self.adapter.start()
            self._connect()
            self._activate_notifications()

            if self.pw:
                cmd = b'\x57\x12' + self.pw
            else:
                cmd = b'\x57\x02'

            # trigger and wait for notification
            value = self._write_cmd_and_wait_for_notification(handle=0x16, cmd=cmd)
            self._handle_switchbot_status_msg(value=value)

            # parse result
            s = {} 

            s["battery"] = value[1]
            s["firmware"] = value[2] / 10.0

            s["n_timers"] = value[8]
            s["dual_state_mode"] = bool(value[9] & 16)
            s["inverse_direction"] = bool(value[9] & 1)
            s["hold_seconds"] = value[10]
        
        finally:
            self.adapter.stop()

        return s

    def get_timers(self, n_timers: int=5) -> List[BaseTimer]:

        try:
            self.adapter.start()
            self._connect()
            self._activate_notifications()

            if self.pw:
                base_cmd = b'\x57\x18' + self.pw
            else:
                base_cmd = b'\x57\x08'

            timers = []

            for i in range(0, n_timers):
                timer_id = (i * 16 + 3).to_bytes(1, byteorder='big')
                cmd = base_cmd + timer_id

                # trigger and wait for notification
                value = self._write_cmd_and_wait_for_notification(handle=0x16, cmd=cmd)
                self._handle_switchbot_status_msg(value=value)

                # parse result
                timer, _ = parse_timer_cmd(value)

                if timer is None: 
                    # timer not set => all later also not set
                    break

                # add to timers
                timers.append(timer)
        
        finally:
            self.adapter.stop()

        return timers

    def encrypted(self, password: str):
        data = password.encode()
        crc = zlib.crc32(data)
        self.pw = crc.to_bytes(4, 'big')

    def _connect(self):
        try:
            self.device = self.adapter.connect(self.mac, address_type=pygatt.BLEAddressType.random)
        except pygatt.BLEError:
            LOG.exception("pygatt: failed to connect to ble device")
            raise SwitchbotError(message="communication with ble device failed")

    
    def _activate_notifications(self):
        uuid = "cba20003-224d-11e6-9fb8-0002a5d5c51b"
        try:
            self.device.subscribe(uuid, callback=handle_notification)
            self.notification_activated = True
        except pygatt.BLEError:
            LOG.exception("pygatt: failed to activate notifications")
            raise SwitchbotError(message="communication with ble device failed")

    def _write_cmd_and_wait_for_notification(self, handle, cmd, notification_timeout_sec=5):
        """
        utility method to write a command to the handle and wait for a notification,
        (requires that notifications are activated)
        """
        if not self.notification_activated:
            raise ValueError("notifications must be activated")

        try:
            # trigger the notification
            self.device.char_write_handle(handle=handle, value=cmd)

            # wait for notification to return
            _, value = notification_queue.get(timeout=notification_timeout_sec)
        
        except pygatt.BLEError:
            LOG.exception("pygatt: failed to write cmd and wait for notification")
            raise SwitchbotError(message="communication with ble device failed")

        return value

    def _handle_switchbot_status_msg(self, value: bytearray):
        """
        checks the status code of the value and raises an exception if the action did not complete

        """
        status = value[0]
        action_status = ActionStatus(status)

        if action_status is not ActionStatus.complete:
            raise SwitchbotError(message=action_status.msg(), switchbot_action_status=action_status)
