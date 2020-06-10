from switchbot import Scanner

def main():
    """scan for switchbots example"""

    scanner = Scanner()
    mac_addresses = scanner.scan()

    if not mac_addresses:
        print("No switchbot found.")
        return

    print("Switchbot mac addresses:")
    for mac in mac_addresses:
        print(mac)


if __name__ == "__main__":
    main()
