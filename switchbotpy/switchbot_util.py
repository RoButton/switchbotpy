import queue
from enum import Enum

notification_queue = queue.Queue()

def handle_notification(handle: int, value: bytes):
    """
    handle: integer, characteristic read handle the data was received on
    value: bytearray, the data returned in the notification
    """
    notification_queue.put((handle, value))

class ActionStatus(Enum):
    complete = 1
    device_busy = 3
    device_unreachable = 11
    device_encrypted  = 7
    device_unencrypted = 8
    wrong_password = 9

    unable_resp = 254
    unable_connect = 255

    def msg(self): 
        if self == ActionStatus.complete:
            msg = "action complete"
        elif self == ActionStatus.device_busy:
            msg = "switchbot is busy"
        elif self == ActionStatus.device_unreachable:
            msg = "switchbot is unreachable"
        elif self == ActionStatus.device_encrypted:
            msg = "switchbot is encrypted"
        elif self == ActionStatus.device_unencrypted:
            msg = "switchbot is unencrypted"
        elif self == ActionStatus.wrong_password:
            msg = "switchbot password is wrong"
        elif self == ActionStatus.unable_resp:
            msg = "switchbot does not respond"
        elif self == ActionStatus.unable_resp:
            msg = "switchbot unable to connect"
        else:
            raise ValueError("unknown action status: " + str(self))

        return msg


class SwitchbotError(Exception):
    def __init__(self, message, switchbot_action_status:ActionStatus=None):
        super().__init__(message)
        self.switchbot_action_status = switchbot_action_status
