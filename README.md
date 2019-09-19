# Switchbot API

One Paragraph of project description goes here

## Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes. See deployment for notes on how to deploy the project on a live system.

### Prerequisites

What things you need to install the software and how to install them

```
Give examples
```

### Installing

A step by step series of examples that tell you how to get a development env running

Say what the step will be

### Usage

#### Simple Usage


Use the scanner to find all switchbots in the area:
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

```
python main.py
```



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
