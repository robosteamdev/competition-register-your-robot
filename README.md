# competition-register-your-robot

![Co-funded by the European Union · ROBO STEAM ACADEMY · partner logos](images/logos_strip.png)

**Erasmus+ project ROBO STEAM ACADEMY** (KA220-VET-7CF4F308) — co-funded by the European Union — <https://robosteam.eu/>

Part of the **PicoBot Teachers' Toolkit** (lesson plans, student materials, slides and guides in five languages):
<https://github.com/robosteamdev/robo-steam-academy-teachers-toolkit>

Connect a **Raspberry Pi Pico W or Pico 2 W** to the competition
server, then claim it on the
[RoboSTEAM competition website](https://competitions.robosteam.eu/).
Your robot's MAC address is its permanent registration number.
Choose its friendly name on the website.

## Hardware

| Part | Details |
|---|---|
| Controller | Raspberry Pi Pico W or Pico 2 W running MicroPython |
| Connection | USB data cable, computer and the [Thonny IDE](https://thonny.org/) |
| Network | 2.4 GHz Wi-Fi with access to the competition broker |

## Files

| File | Upload to the Pico? |
|---|---|
| `register_robot.py` | Yes — run once to register and answer connection tests |
| `credentials.py.example` | Yes — edit and save privately as `credentials.py` |
| `show_mac.py` | Yes, optional — display the address without connecting |
| `tests/test_register_robot.py` | No — checks on a computer with Python |
| `README.md`, `LICENSE`, `.gitignore`, `images/logos_strip.png` | No — documentation, licence and repository files |

## How to use

### What you need

- A Pico **W** or Pico **2 W** with MicroPython installed.
- A USB cable that carries data, a computer, and the **Thonny IDE** (free, <https://thonny.org/>).
- A 2.4 GHz Wi-Fi network that can reach the competition broker.
- The broker address, port, username and password from your organiser.
- A team or participant login for the competition website.

A Pico without **W** has no Wi-Fi. This tool only registers the
board; use your competition program afterwards to drive the robot.

### 1. Connect the Thonny IDE to your Pico

Plug in the Pico. Open the Thonny IDE and choose the **MicroPython
(Raspberry Pi Pico)** interpreter using the interpreter selector
at the bottom right (or **Tools -> Options -> Interpreter**).
Select your board's USB/serial port. Press **Stop/Restart backend**
to interrupt any program already running. Keep the robot stationary.

If MicroPython is missing, ask your teacher to install the firmware
for your exact board, **Pico W** or **Pico 2 W**. Back up existing
robot files before reinstalling firmware.

Open **View -> Files** to see the computer and Pico file lists.
The [Thonny MicroPython guide](https://github.com/thonny/thonny/wiki/MicroPython)
explains interpreter selection and file transfer.

### 2. Put the files on the Pico

Download this repository and unpack it on your computer.
Open `credentials.py.example` in the Thonny IDE, then use
**File -> Save as -> Raspberry Pi Pico** to save it as
**`credentials.py`** in the Pico's top folder.

Open `register_robot.py` and save it to the Pico's top folder
with the same name. You may also save `show_mac.py` there if you
want a separate address-only tool. You do not need to copy the
tests, README or license to the Pico.

Do not rename this program to `main.py`: it should run only when
you ask it to. Keep your existing competition program.
If a `credentials.py` already exists, save a private backup before
replacing it; your competition program may use that file too.

Some MicroPython builds include `umqtt.simple`; others need it
installed. To check, type this in the Thonny IDE Shell:

```python
from umqtt.simple import MQTTClient
```

If you see `ImportError`, ask your teacher to install the official
[umqtt.simple package](https://github.com/micropython/micropython-lib/tree/master/micropython/umqtt.simple).
With Wi-Fi connected, a teacher can use MicroPython's package
installer in the Pico REPL:

```python
import mip
mip.install("umqtt.simple")
```

That installation needs internet access on the Pico. For an offline
Pico, the teacher can copy the package's `umqtt/simple.py` into
`/lib/umqtt/simple.py` using the Thonny IDE, keeping the `umqtt` folder.
The package is a separate dependency; it is not included here.

### 3. Edit settings for this location

Open **the Pico's** `credentials.py`. Change the Wi-Fi name and
password between the quotes. Start with the example file:

```python
WIFI_SSID = "your-wifi-name"
WIFI_PASSWORD = "your-wifi-password"
```

For venue Wi-Fi or a phone hotspot, replace both values. Keep
quotes around text and save the file on the Pico after editing.

Ask your organiser to fill in these settings too:

```python
MQTT_BROKER = "your-broker-address"
MQTT_PORT = 1883
MQTT_USER = "your-mqtt-username"
MQTT_PASSWORD = "your-mqtt-password"
```

Replace all three placeholder strings. Use the organiser's actual
port as a number, without quotes; 1883 is only the example port.
The broker address is a host name or IP, without `https://`,
`mqtt://`, a path or a port appended to it. This program uses
plain TCP MQTT, so ask for that endpoint rather than a website,
WebSocket or TLS endpoint.

No robot name or category number belongs in this file.
Keep `credentials.py` private. The example contains no real MQTT
password and `.gitignore` excludes the private file.
After changing credentials, press **Stop/Restart backend** before
running again, so MicroPython reloads the saved values.

**Phone hotspot tip:** enable mobile data and select **2.4 GHz**
or the phone's compatibility option. Keep the phone nearby with
the hotspot enabled. A 5 GHz-only hotspot will not work. Your
organiser must provide a broker reachable from that hotspot;
a private venue address might work only on venue Wi-Fi.

### 4. Run once

Open `register_robot.py` on the Pico. Click the Thonny IDE's green **Run**
button (F5). Watch the Shell. The MAC appears even if the settings
still need editing. Wi-Fi gets up to three attempts of 20 seconds
each. Dots and a slow LED blink show progress while connecting.

The program sends three registration heartbeats two seconds apart.
It then listens for website connection tests for ten seconds and
finishes. The LED stays on after all three messages are delivered.

An example successful first run is below. Your MAC will differ;
Wi-Fi dots depend on how long your connection takes. This example
shows an immediate Wi-Fi connection and no website test:

```text

RoboSTEAM - Register my robot
+------------------------------------------+
Your robot's MAC address: AA:BB:CC:DD:EE:FF
+------------------------------------------+
Connecting Wi-Fi 1/3
Wi-Fi OK
Connecting to the competition broker...
Broker connected.
Heartbeat 1/3 delivered to broker.
Heartbeat 2/3 delivered to broker.
Heartbeat 3/3 delivered to broker.
Heartbeats sent; no automatic server reply.
Listening for website Test connection (10 s).
+------------------------------------------+
Wi-Fi OK
Server OK: broker received 3 heartbeats.
Server registration: check on the website.
MAC: AA:BB:CC:DD:EE:FF
https://competitions.robosteam.eu/
My Robots -> claim a robot -> paste this MAC.
Choose a name there; change it with Rename.
+------------------------------------------+
Done. Registration stays after this program ends.
Online status expires; use competition code to race.
```

**What success means:** the MQTT broker acknowledged the three
messages. The competition server normally registers the robot
from those heartbeats. It does not automatically reply to the
robot, so confirm registration by claiming the MAC on the website.
Broker delivery alone cannot prove that the server saved it.

You can also start a file already saved on the Pico from its REPL:

```python
import register_robot
```

An import runs once per MicroPython session. For another run in
the same session, use `register_robot.run()`. After editing settings,
restart the backend first to reload them.

If it gets stuck connecting to the broker or waiting for a message
acknowledgement, press **Stop** (or Ctrl+C in the Shell), check the
network and settings, and run again. The Wi-Fi attempts have a
20-second limit; `umqtt.simple` socket operations depend on the
firmware's network timeouts and may take longer.

### 5. Claim your robot on the website

1. Open [competitions.robosteam.eu](https://competitions.robosteam.eu/)
   and sign in with your team or participant account.
2. Open **My Robots -> claim a robot**.
3. Paste the MAC exactly, including its colons.
4. Choose a friendly name and confirm. You can change it later
   with **Rename**.
5. Follow your competition's instructions to assign this robot to
   your team/category, then run the normal competition program.

The device's registration remains after this tool stops. Its online
indicator can later expire because this one-shot tool has stopped
sending heartbeats. That does not erase the registration.

For an optional live test, claim the robot, run this tool again,
and press **Test connection** on My Robots while the tool is
running. A server PING makes the tool print:

```text
Website PING received; PONG sent.
```

Its final box then includes `Website connection test answered.`
The website shows whether the server received the PONG. The tool
does not receive an acknowledgement of that database update.
It ignores START and STOP commands and never drives motors.

## Only need the MAC?

Run `show_mac.py` in the Thonny IDE. It prints the same framed address
without logging into Wi-Fi, contacting the server or reading
credentials. Write the address on a sticker for the robot.

## Troubleshooting

| Message or symptom | What to do |
|---|---|
| Missing `credentials.py` | Save the example as exactly `credentials.py` on the Pico, beside `register_robot.py`. |
| `Edit ... in credentials.py` | Edit the named setting; fill placeholders, check quotes, then save and restart the backend. |
| Wrong password | Edit `WIFI_PASSWORD`; passwords are case-sensitive. |
| Network not found | Check `WIFI_SSID`, spelling, range and router power. |
| 5 GHz-only Wi-Fi | Enable 2.4 GHz on the router or hotspot. Pico cannot tell a hidden 5 GHz network from an absent network. |
| Wi-Fi failed / three attempts end | Move closer, check the router and credentials, then run again. Some firmware reports only a general failure. |
| Wi-Fi OK but server fails | Check internet on a phone on the same network. Complete any venue sign-in or use a hotspot. Check that the organiser's broker is reachable from this network. |
| Internet works but server fails | Ask the organiser to check broker host, TCP port, MQTT username/password, firewall and broker service. |
| Broker acknowledged messages but MAC cannot be claimed | Check the copied MAC. Ask the organiser to check the server's MQTT bridge and that you used the correct broker. |
| Robot already claimed | Ask its owner or organiser to release it; do not change the MAC. |
| `umqtt.simple` missing | Ask your teacher to install the official package as described in step 2. |
| Waiting too long for the broker | Press Stop/Ctrl+C, check settings and network, then retry. MQTT socket operations may wait longer than Wi-Fi. |
| LED does not blink | Read the Shell; LED support is optional. |
| Online status disappears after finishing | Expected: this tool exits. Use the competition program to stay online. |
| `import register_robot` does nothing the second time | Use `register_robot.run()` or restart the backend and import again. |
| Old competition program runs on power-up | An existing `main.py` runs automatically; press Stop in the Thonny IDE before running this tool. |

The Pico cannot reliably distinguish lost internet from a blocked
port, incorrect broker address or stopped broker. It gives checks
for these possibilities instead of guessing the cause.

## Settings

| Setting | Meaning | Example default |
|---|---|---|
| `WIFI_SSID` | Your 2.4 GHz network name | `your-wifi-name` |
| `WIFI_PASSWORD` | Your network password | `your-wifi-password` |
| `MQTT_BROKER` | Plain TCP broker host from the organiser | `your-broker-address` |
| `MQTT_PORT` | Broker TCP port, supplied by the organiser | `1883` |
| `MQTT_USER` | Broker login | `your-mqtt-username` |
| `MQTT_PASSWORD` | Broker password | `your-mqtt-password` |

## Checks for teachers

On a computer with Python, from this repository:

```console
python -B -m unittest discover -s tests -v
```

These tests use fake hardware and MQTT objects. They do not contact a broker.

## Licence and credits

Code: MIT Licence (see `LICENSE`).
Please credit "ROBO STEAM ACADEMY, Erasmus+ project KA220-VET-7CF4F308" — <https://robosteam.eu/>.

MicroPython and the separately installed `umqtt.simple` package retain their own licences; neither is bundled here.

Funded by the European Union. Views and opinions expressed are however those of the author(s) only and do not
necessarily reflect those of the European Union or the Human Resource Development Centre (HRDC). Neither the European
Union nor the granting authority can be held responsible for them.
