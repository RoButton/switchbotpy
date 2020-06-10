"""
Scan and control Switchbots via BLE:
- control actions (press, switch on, switch off)
- control settings (set hold time, set mode,
  get battery, get firmware, get hold seconds, get mode, get number of timers)
- control timers (get and set timers + sync timestamps)

All operations support using a predefined password (configured via the official Switchbot App)
"""

import logging
import re
import time
import zlib
from binascii import hexlify
from typing import Any, Dict, List, Tuple
from uuid import UUID

import pygatt

from switchbotpy.switchbot_timer import BaseTimer, delete_timer_cmd, parse_timer_cmd
from switchbotpy.switchbot_util import (ActionStatus, SwitchbotError, handle_notification,
                            notification_queue)


logging.basicConfig()
LOG = logging.getLogger('switchbot')

class Scanner(object):
    """ Switchbot Scanner class to scan for available switchbots (might require root privileges)"""

    def __init__(self):
        self.adapter = pygatt.GATTToolBackend()

    def scan(self, known_dict=None) -> List[str]:
        """Scan for available switchbots"""
        LOG.info("scanning for bots")
        try:
            self.adapter.start()
            devices = self.adapter.scan()
        finally:
            self.adapter.stop()

        switchbots = []

        for device in devices:
            if device['address'] is not None:
                # mac of device is known
                # -> don't need to check characteristics to know if device is a switchbot
                if known_dict[device['address']]:
                    switchbots.append(device['address'])
            elif self._is_switchbot(mac=device['address']):
                 # mac of device is unknown
                 # -> check characteristics to know if device is a switchbot
                switchbots.append(device['address'])

        return switchbots

    def _is_switchbot(self, mac: str) -> bool:
        try:
            self.adapter.start()
            device = self.adapter.connect(mac, address_type=pygatt.BLEAddressType.random)
            characteristics = self.adapter.discover_characteristics(device)
            device.disconnect()

            uuid1 = UUID("{cba20002-224d-11e6-9fb8-0002a5d5c51b}")
            uuid2 = UUID("{cba20003-224d-11e6-9fb8-0002a5d5c51b}")

            is_switchbot = uuid1 in characteristics.keys() and  uuid2 in characteristics.keys()
        except pygatt.exceptions.NotConnectedError:
            # e.g. if device uses different addressing
            is_switchbot = False
        finally:
            self.adapter.stop()

        return is_switchbot


class Bot(object):
    """Switchbot class to control the bot."""

    def __init__(self, bot_id: int, mac: str, name: str):

        if not re.match(r"[0-9A-F]{2}(?:[-:][0-9A-F]{2}){5}$", mac):
            raise ValueError("Illegal Mac Address: ", mac)

        self.bot_id = bot_id
        self.mac = mac
        self.name = name

        self.adapter = pygatt.GATTToolBackend()
        self.device = None
        self.password = None
        self.notification_activated = False

        LOG.info("create bot: id=%d mac=%s name=%s", self.bot_id, self.mac, self.name)

    def press(self):
        """Press the Switchbot in the standard mode (non dual state mode):
            1. Extend arm
            2. Hold for configured number of seconds [see set_hold_time()]
            3. Retract arm
        """
        LOG.info("press bot")
        try:
            self.adapter.start()
            self._connect()
            self._activate_notifications()

            if self.password:
                cmd = b'\x57\x11' + self.password
            else:
                cmd = b'\x57\x01'

            value = self._write_cmd_and_wait_for_notification(handle=0x16, cmd=cmd)
            self._handle_switchbot_status_msg(value=value)

        finally:
            self.adapter.stop()


    def switch(self, switch_on: bool):
        """Switch the state of the Switchbot in the dual state mode:
            (Extend arm or Retract arm)
        """

        LOG.info("switch bot on=%s", str(switch_on))
        try:
            self.adapter.start()
            self._connect()
            self._activate_notifications()

            if self.password:
                cmd = b'\x57\x11' + self.password
            else:
                cmd = b'\x57\x01'

            if switch_on:
                cmd += b'\x01'
            else: # off
                cmd += b'\x02'

            value = self._write_cmd_and_wait_for_notification(handle=0x16, cmd=cmd)
            self._handle_switchbot_status_msg(value=value)

        finally:
            self.adapter.stop()


    def set_hold_time(self, sec: int):
        """Set the hold time for the Switchbot in the standard mode (up to one minute)"""

        LOG.info("set hold time: %d sec", sec)
        if sec < 0 or sec > 60:
            raise ValueError("hold time must be between [0, 60] seconds")

        try:
            self.adapter.start()
            self._connect()
            self._activate_notifications()

            if self.password:
                cmd = b'\x57\x1f' + self.password
            else:
                cmd = b'\x57\x0f'

            cmd += b'\x08' + sec.to_bytes(1, byteorder='big')

            value = self._write_cmd_and_wait_for_notification(handle=0x16, cmd=cmd)
            self._handle_switchbot_status_msg(value=value)

        finally:
            self.adapter.stop()

    def get_timer(self, idx: int) -> Tuple[BaseTimer, int]:
        """Get all the configured timers of the Switchbot."""

        LOG.info("get timer: %d", idx)
        try:
            self.adapter.start()
            self._connect()
            self._activate_notifications()

            if self.password:
                cmd = b'\x57\x18' + self.password
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
        """Configure Switchbot timer."""

        LOG.info("set timer: %d", idx)
        if idx < 0 or idx > 4 or num_timer <= idx or num_timer < 1 or num_timer > 5:
            raise ValueError("Illegal Timer Idx or Number of Timers")
        try:
            self.adapter.start()
            self._connect()
            self._activate_notifications()

            if self.password:
                cmd = b'\x57\x19' + self.password
            else:
                cmd = b'\x57\x09'

            cmd += timer.to_cmd(idx=idx, num_timer=num_timer)
            value = self._write_cmd_and_wait_for_notification(handle=0x16, cmd=cmd)
            self._handle_switchbot_status_msg(value=value)

        finally:
            self.adapter.stop()


    def set_timers(self, timers: List[BaseTimer]):
        """Configure multiple Switchbot timers."""

        LOG.info("set timers")
        try:
            self.adapter.start()
            self._connect()
            self._activate_notifications()

            if self.password:
                cmd_base = b'\x57\x19' + self.password
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
        """Sync the timestamps for the timers."""

        LOG.info("setting current timestamp")
        try:
            self.adapter.start()
            self._connect()
            self._activate_notifications()

            if self.password:
                cmd_base = b'\x57\x19' + self.password
            else:
                cmd_base = b'\x57\x09'

            time_sec_utc = time.time()
            time_local = time.localtime(time_sec_utc)
            offset = time_local.tm_gmtoff
            timestamp = int(time_sec_utc + offset)

            cmd = cmd_base + b'\x01'
            cmd += timestamp.to_bytes(8, byteorder='big')

            value = self._write_cmd_and_wait_for_notification(handle=0x16, cmd=cmd)
            self._handle_switchbot_status_msg(value=value)

        finally:
            self.adapter.stop()


    def set_mode(self, dual_state: bool, inverse: bool):
        """Change the switchbot mode:
            Standard Mode:  press() -> Extend / Hold / Retract arm
            Dual State Mode: 1. Extend arm with switch(on=True) 2. Retract arm with switch(on=False)
            Inverse: The Arm is extended by default and retracts on press()
        """
        LOG.info("setting mode: dual_state=%s  inverse=%s", str(dual_state), str(inverse))
        LOG.info("  resetting all timers")

        # delete all timers
        # -> because if dual_state changes, then also action of timer needs to change
        self.set_timers(timers=[])

        try:
            self.adapter.start()
            self._connect()
            self._activate_notifications()

            if self.password:
                cmd_base = b'\x57\x13' + self.password
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
        """
        Get the Switchbot settings (battery, firmware, number of timers,
        mode (standard / dual state), inverse mode, hold seconds)"""

        LOG.info("get settings")
        try:
            self.adapter.start()
            self._connect()
            self._activate_notifications()

            if self.password:
                cmd = b'\x57\x12' + self.password
            else:
                cmd = b'\x57\x02'

            # trigger and wait for notification
            value = self._write_cmd_and_wait_for_notification(handle=0x16, cmd=cmd)
            self._handle_switchbot_status_msg(value=value)

            # parse result
            settings = {}

            settings["battery"] = value[1]
            settings["firmware"] = value[2] / 10.0

            settings["n_timers"] = value[8]
            settings["dual_state_mode"] = bool(value[9] & 16)
            settings["inverse_direction"] = bool(value[9] & 1)
            settings["hold_seconds"] = value[10]

        finally:
            self.adapter.stop()

        return settings

    def get_timers(self, n_timers: int = 5) -> List[BaseTimer]:
        """Get the configured Switchbot timers"""

        LOG.info("get timers")
        try:
            self.adapter.start()
            self._connect()
            self._activate_notifications()

            if self.password:
                base_cmd = b'\x57\x18' + self.password
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
        """The Switchbot is configured with this password."""

        LOG.info("use encrypted communication")
        data = password.encode()
        crc = zlib.crc32(data)
        self.password = crc.to_bytes(4, 'big')

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
        LOG.debug("handle: %s cmd: %s", str(hex(handle)), str(hexlify(cmd)))

        try:
            # trigger the notification
            self.device.char_write_handle(handle=handle, value=cmd)

            # wait for notification to return
            _, value = notification_queue.get(timeout=notification_timeout_sec)

        except pygatt.BLEError:
            LOG.exception("pygatt: failed to write cmd and wait for notification")
            raise SwitchbotError(message="communication with ble device failed")


        LOG.debug("handle: %s cmd: %s notification: %s",
                  str(hex(handle)), str(hexlify(cmd)), str(hexlify(value)))
        return value

    def _handle_switchbot_status_msg(self, value: bytearray):
        """
        checks the status code of the value and raises an exception if the action did not complete
        """

        status = value[0]
        action_status = ActionStatus(status)

        if action_status is not ActionStatus.complete:
            raise SwitchbotError(message=action_status.msg(), switchbot_action_status=action_status)
