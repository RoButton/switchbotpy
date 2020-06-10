import argparse

from switchbot import Bot

def main(config):
    """press switchbot example"""

    # initialize bot
    bot = Bot(bot_id=0, mac=config.mac, name="bot0")
    if config.password:
        bot.encrypted(password=config.password)

    # execute get settings command
    print("get settings...")
    settings = bot.get_settings()
    print("  battery: ", settings["battery"])
    print("  firmware: ", settings["firmware"])
    print("  hold seconds: ", settings["hold_seconds"])
    print("  timer count: ", settings["n_timers"])
    print("  dual state mode: ", settings["dual_state_mode"])
    print("  inverse direction: ", settings["inverse_direction"])

    # execute set settings commands
    print("set settings...")

    # adjust hold time
    if config.hold:
        bot.set_hold_time(sec=config.hold)

    # adjust mode and inverse
    if config.mode or config.inverse:
        if not config.mode:
            dual = settings["dual_state_mode"]
        elif config.mode == 'standard':
            dual = False
        elif config.mode == 'dual':
            dual = True
        else:
            raise ValueError("Unknown config.mode: ", config.mode)

        if not config.inverse:
            config.inverse = settings["inverse_direction"]
        
        bot.set_mode(dual_state=dual, inverse=config.inverse)



if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mac", help="mac address of switchbot")
    parser.add_argument("--password", help="password of switchbot")
    parser.add_argument("--hold", help="press hold seconds of switchbot", type=int)
    mode_choices = ['standard', 'dual']
    parser.add_argument("--mode", help="mode of switchbot", choices=mode_choices)
    parser.add_argument("--inverse", help="inverse state", nargs=0)
    args = parser.parse_args()
    if not args.mac:
        args.mac = input("Enter mac address of switchbot: ")

    if not args.hold:
        try:
            args.hold = int(input("Enter hold seconds (skip with enter): "))
        except ValueError:
            pass
    if not args.mode:
        mode = input("Enter switchbot mode [standard/dual]: ")
        if mode in mode_choices:
            args.mode = mode

    if not args.inverse:
        inverse = input("Inverse? [y/n]")
        inverse = inverse.lower().strip()
        if inverse == 'y':
            args.inverse = True
        elif inverse == 'n':
            args.inverse = False

    main(config=args)