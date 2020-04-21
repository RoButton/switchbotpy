# Switchbot API

A REST and Python API for  [SwitchBots](https://www.switch-bot.com/) which allows to control actions, settings and timers.

Among other possibilities, setting up a webserver on a RaspberryPi in combination with an app capable of sending custom HTTP requests (e.g. [HTTP-Shortcuts](https://github.com/Waboodoo/HTTP-Shortcuts) for Android), allows to control SwitchBots by phone outside of the BLE range (without a Hub).

## Getting Started

### Prerequisites

The setup is tested on a RaspberryPi 3 with the Raspbian Buster OS in combination with SwitchBots running firmware 4.4 and 4.5

### Installing

Install pipenv if you don't have it and then install the environment from the `Pipfile` (from the root directory):
```
pip install pipenv
```
```
pipenv install
```

Afterwards, Flask can be started with the following command:
```
pipenv run python src/main.py
```

Note that if you observe the following error: `Can't init device hci0: Connection timed out (110)` while running either of the APIs. Update all packages, reinstall the pipenv and reboot your machine [see these steps](https://github.com/nicolas-kuechler/switchbot/issues/13#issuecomment-617072613).

### Usage

#### Python API


Use the scanner to find all SwitchBots in the area:
```python
from switchbot import Scanner

scanner = Scanner()
mac_addresses = scanner.scan(known_dict={})
```

Use the mac address to create a bot instance providing methods to control the switchbots:
```python
from switchbot import Bot

bot = Bot(id=bot_id, mac=mac, name=name)
bot.encrypted(password) # optional (only required in case the bot has a password)

bot.press() # press the switchbot
settings = bot.get_settings() # get a dict with the current bot settings

# all other options can be found in the switchbot.py file
```

#### Flask REST API

The REST API uses the Python API to communicate with the SwitchBots.


The following endpoints are available:

| Name                                       | Method | Endpoint                                          |
| ------------------------------------------ |--------| ------------------------------------------------- |
| Login (use password to receive token)      | POST   | ` /switchbot/api/v1/login`                        |
| Perform Action (press, turn on, turn off)  | POST   | `/switchbot/api/v1/bot/{bot_id}/actions`          |
| Find all SwitchBots                        | GET    | `/switchbot/api/v1/bots`                          |
| Get Settings                               | GET    | `/switchbot/api/v1/bot/{bot_id}`                  |
| Update Settings                            | PATCH  | `/switchbot/api/v1/bot/{bot_id}`                  |
| Get all timers                             | GET    | `/switchbot/api/v1/bot/{bot_id}/timers`           |
| Add a timer                                | POST   | `/switchbot/api/v1/bot/{bot_id}/timers`           |
| Update multiple timers at once             | PATCH  | `/switchbot/api/v1/bot/{bot_id}/timers` |
| Update a timer                             | PATCH  | `/switchbot/api/v1/bot/{bot_id}/timer/{timer_id}` |
| Delete Timer                               | DELETE | `/switchbot/api/v1/bot/{bot_id}/timer/{timer_id}` |


To get more details about how to use the REST API, start the Flask app with: `pipenv run python src/main.py` and then use the endpoint `/doc/openapi.json` to obtain a [OPEN API](https://www.openapis.org/) specification.

Additionally, I provide a Postman collection in the `/postman` folder which can be imported to try the API. (Start with the Login request to obtain a bearer token which is used for all other endpoints. Afterwards use the update settings endpoint to specify the password set with the switchbot app)

## Deployment

For the deployment of the Switchbot REST API it is recommended to run the Flask application in combination with Nginx and Gunicorn.


## Switchbot BLE API

For people interested in building an application controlling their switchbots, I provide a list with the results of my reverse engineering. I do not guarantee correctness nor completeness but with the BLE commands as described below I managed to control switchbots with firmware 4.4 and 4.5.
The official switchbot app was used to set the password of the bots.

### Actions

 <table>
  <tr>
    <th></th>
    <th colspan="3">Request</th>
    <th colspan="3">Notification (Response)</th>
  </tr>
  <tr>
    <th>Name</th>
    <th>Handle</th>
    <th>Unencrypted</th>
    <th>Encrypted</th>
    <th>Required</th>
    <th>Handle</th>
    <th>Value</th>
  </tr>
  <tr>
    <td>press</td>
    <td rowspan="3">0x16</td>
    <td>0x 57 01</td>
    <td>0x 57 11 <code>pw<sub>8</sub></code></td>
    <td></td>
    <td rowspan="3">0x13</td>
    <td rowspan="3"><code>stat<sub>2</sub></code></td>
  </tr>
  <tr>
    <td>turn on</td>
    <td>0x 57 01 01</td>
    <td>0x 57 11 <code>pw<sub>8</sub></code> 01</td>
    <td></td>
  </tr>
  <tr>
    <td>turn off</td>
    <td>0x 57 01 02</td>
    <td>0x 57 11 <code>pw<sub>8</sub></code> 02</td>
    <td></td>
  </tr>
</table>

- <code>pw<sub>8</sub></code>: crc32 checksum of the password in 4 bytes
- <code>stat<sub>2</sub></code>: 1 = action complete, 3 = bot busy, 11 = bot unreachable, 7 = bot encrypted, 8 = bot unencrypted, 9 = wrong password

### Settings
#### GET Settings

The bot settings are all retrieved by triggering one notification which consists of the concatenated settings.

<table>
 <tr>
   <th></th>
   <th colspan="3">Request</th>
   <th colspan="3">Notification (Response)</th>
 </tr>
 <tr>
   <th>Name</th>
   <th>Handle</th>
   <th>Unencrypted</th>
   <th>Encrypted</th>
   <th>Required</th>
   <th>Handle</th>
   <th>Value</th>
 </tr>
 <tr>
   <td>get settings</td>
   <td rowspan="7">0x16</td>
   <td rowspan="7">0x 57 02</td>
   <td rowspan="7">0x 57 12 <code>pw<sub>8</sub></code></td>
   <td rowspan="7">x</td>
   <td rowspan="7">0x13</td>
   <td> 0x <code>stat<sub>2</sub></code> <code>bat<sub>2</sub></code> <code>fw<sub>2</sub></code> 64 00 00 00 00 <code>nt<sub>2</sub></code> <code>ds<sub>1</sub></code> <code>inv<sub>1</sub></code> <code>sec<sub>2</sub></code> </td>
 </tr>
  <tr>
    <td>battery</td>
    <td><code>bat<sub>2</sub></code>: 1st byte of value</td>
  </tr>
  <tr>
    <td>firmware</td>
    <td><code>fw<sub>2</sub></code>: 2nd byte of value (div by 10)</td>
  </tr>
  <tr>
    <td>number of timers</td>
    <td><code>nt<sub>2</sub></code>: 8th byte of value</td>
  </tr>
  <tr>
    <td>dual state mode</td>
    <td><code>ds<sub>1</sub></code>: first 4 bits of 9th byte of value</td>
  </tr>
  <tr>
    <td>inverse direction</td>
    <td><code>inv<sub>1</sub></code>: last 4 bits of 9th byte of value</td>
  </tr>
  <tr>
    <td>hold seconds</td>
    <td><code>sec<sub>2</sub></code>: 10th byte of value</td>
  </tr>

</table>

 - <code>pw<sub>8</sub></code>: crc32 checksum of the password in 4 bytes
 - <code>stat<sub>2</sub></code>: 1 = action complete, 3 = bot busy, 11 = bot unreachable, 7 = bot encrypted, 8 = bot unencrypted, 9 = wrong password

#### SET Settings

<table>
<tr>
   <th></th>
   <th colspan="3">Request</th>
   <th colspan="3">Notification (Response)</th>
 </tr>
 <tr>
   <th>Name</th>
   <th>Handle</th>
   <th>Unencrypted</th>
   <th>Encrypted</th>
   <th>Required</th>
   <th>Handle</th>
   <th>Value</th>
 </tr>
  <tr>
    <td>hold time</td>
    <td rowspan="2">0x16</td>
    <td>0x 57 0f 08 <code>sec<sub>2</sub></code></td>
    <td>0x 57 1f <code>pw<sub>8</sub></code> 08 <code>sec<sub>2</sub></code></td>
    <td></td>
    <td rowspan="2">0x13</td>
    <td rowspan="2"><code>stat<sub>2</sub></code></td>
  </tr>
  <tr>
    <td>mode</td>
    <td>0x 57 03 64  <code>ds<sub>1</sub></code><code>inv<sub>1</sub></code></td>
    <td>0x 57 13 64 <code>pw<sub>8</sub></code> <code>ds<sub>1</sub></code><code>inv<sub>1</sub></code></td>
    <td></td>
  </tr>
</table>

- <code>pw<sub>8</sub></code>: crc32 checksum of the password in 4 bytes
- <code>sec<sub>2</sub></code>: seconds as one byte unsigned int
- <code>ds<sub>1</sub></code>: if dual state mode: 1 else 0
- <code>inv<sub>1</sub></code>: if inverse mode: 1  else 0
- <code>stat<sub>2</sub></code>: 1 = action complete, 3 = bot busy, 11 = bot unreachable, 7 = bot encrypted, 8 = bot unencrypted, 9 = wrong password

### Timers
<table>
 <tr>
   <th></th>
   <th colspan="3">Request</th>
   <th colspan="3">Notification (Response)</th>
 </tr>
 <tr>
   <th>Name</th>
   <th>Handle</th>
   <th>Unencrypted</th>
   <th>Encrypted</th>
   <th>Required</th>
   <th>Handle</th>
   <th>Value</th>
 </tr>
  <tr>
    <td>get timer</td>
    <td rowspan="3">0x16</td>
    <td>0x 57 08 <code>tid<sub>1</sub></code>3</td>
    <td>0x 57 18 <code>pw<sub>8</sub></code> <code>tid<sub>1</sub></code>3</td>
    <td>x</td>
    <td rowspan="3">0x13</td>
    <td></td>
  </tr>
  <tr>
    <td>set timer</td>
    <td>0x 57 09 <code>tid<sub>1</sub></code>3 <code>timer<sub>20</sub></code></td>
    <td>0x 57 19 <code>pw<sub>8</sub></code> <code>tid<sub>1</sub></code>3 <code>timer<sub>20</sub></code></td>
    <td></td>
    <td><code>stat<sub>2</sub></code></td>
  </tr>
  <tr>
    <td>sync timer</td>
    <td>0x 57 09 01 <code>t<sub>16</sub></code></td>
    <td>0x 57 19 <code>pw<sub>8</sub></code> 01 <code>t<sub>16</sub></code></code></td>
    <td></td>
    <td><code>stat<sub>2</sub></code></td>
  </tr>
</table>

- <code>pw<sub>8</sub></code>: crc32 checksum of the password in 4 bytes
- <code>tid<sub>1</sub></code>: timer id between 0 and 4
- <code>timer<sub>20</sub></code>:  <code>nt<sub>2</sub></code> 00 <code>rep<sub>2</sub></code> <code>hh<sub>2</sub></code> <code>mm<sub>2</sub></code> <code>rep1<sub>1</sub></code><code>md<sub>1</sub></code>  <code>rep2<sub>1</sub></code><code>act<sub>1</sub></code> <code>its<sub>2</sub></code> <code>ihh<sub>2</sub></code> <code>imm<sub>2</sub></code>
- <code>nt<sub>2</sub></code>: number of timers as one byte (e.g. 0x03 if there are 3 timers set)
- <code>rep<sub>2</sub></code>: repeating pattern as one byte. Is 0x00 if timer is disabled. Is 0x80==b10000000 if there is no repetition. Otherwise, the last seven bits of the byte indicate the weekday on which the timer should be repeated (e.g. b01100000 means that the timer counts for Sunday and Saturday).
- <code>hh<sub>2</sub></code>: timer hour between 0 and 23
- <code>mm<sub>2</sub></code>: timer minute between 0 and 59
- <code>rep1<sub>1</sub></code>: in case the timer is disabled (<code>rep<sub>2</sub></code>=0), the first 4 bits of the repeating byte are stored here
- <code>md<sub>1</sub></code>: timer mode (standard=0, interval=1) as a byte,
- <code>rep2<sub>1</sub></code>: in case the timer is disabled (<code>rep<sub>2</sub></code>=0), the last 4 bits of the repeating byte are stored here
- <code>act<sub>1</sub></code>: timer action (press=0, turn_on=1, turn_off=2) as a byte
- <code>its<sub>2</sub></code>: interval timer sum
- <code>ihh<sub>2</sub></code>: interval timer hour
- <code>imm<sub>2</sub></code>: interval timer minutes
- <code>stat<sub>2</sub></code>: 1 = action complete, 3 = bot busy, 11 = bot unreachable, 7 = bot encrypted, 8 = bot unencrypted, 9 = wrong password


## Authors

* **Nicolas Küchler** - *Initial work* - [nicolas-kuechler](https://github.com/nicolas-kuechler)
