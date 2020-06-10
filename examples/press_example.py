import argparse

from switchbotpy import Bot

def main(config):
    """press switchbot example"""

    # initialize bot
    bot = Bot(bot_id=0, mac=config.mac, name="bot0")
    if config.password:
        bot.encrypted(password=config.password)

    # execute press command
    bot.press()



if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mac", help="mac address of switchbot")
    parser.add_argument("--password", help="password of switchbot")
    args = parser.parse_args()
    if not args.mac:
        args.mac = input("Enter mac address of switchbot: ")

    main(config=args)
