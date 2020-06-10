import argparse

from switchbotpy import Bot
from switchbotpy import StandardTimer
from switchbotpy import Action

def main(config):
    """timers switchbot example"""

    # initialize bot
    bot = Bot(bot_id=0, mac=config.mac, name="bot0")
    if config.password:
        bot.encrypted(password=config.password)

    print("get timers...")
    timers = bot.get_timers()
    for i, timer in enumerate(timers):
        timer_dict = timer.to_dict(timer_id=i)
        print("  timer: ", timer_dict["id"])
        print("    mode: ", timer_dict["mode"])
        print("    action: ", timer_dict["action"])
        print("    enabled: ", timer_dict["enabled"])
        print("    weekdays: ", timer_dict["weekdays"])
        print("    hour: ", timer_dict["hour"])
        print("    minute: ", timer_dict["min"])


    print("set timers...")
    timer = StandardTimer(action=Action["press"], # Action["turn_on"], Action["turn_off"]  
                          enabled=True,
                          weekdays=[1, 2, 5],
                          hour=15,
                          min=30)
    try:
        t_id = int(input("Enter timer id: [0,5): "))
        if t_id >= 5:
            raise ValueError()
    
        if t_id >= len(timers):
            timers.append(timer)
        else:
            timers[t_id] = timer

        bot.set_timers(timers)
        print("  updated timers")
    except ValueError:
        print("  skip updating timers")

    if config.clear:
        print("clearing all timers from switchbot")
        bot.set_timers([])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mac", help="mac address of switchbot")
    parser.add_argument("--password", help="password of switchbot")
    parser.add_argument("--clear", help="clear all timers in the end")

    args = parser.parse_args()
    if not args.mac:
        args.mac = input("Enter mac address of switchbot: ")

    main(config=args)
