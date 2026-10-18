"""Run once in the Thonny IDE, or import register_robot on a Pico W.

Hardware imports stay in run() so helpers can be tested on a PC.
This program never controls motors or changes a robot's name.
"""

import json

FIRMWARE_VERSION = "register-robot-1.0"
SETTING_NAMES = (
    "WIFI_SSID", "WIFI_PASSWORD", "MQTT_BROKER", "MQTT_PORT",
    "MQTT_USER", "MQTT_PASSWORD",
)


def format_mac(raw):
    """Turn the six hardware bytes into the website's address."""
    if len(raw) != 6:
        raise ValueError("A MAC address needs six bytes.")
    return ":".join("%02X" % part for part in raw)


def validate_credentials(settings):
    """Return errors naming settings, never their private values."""
    errors = []
    for name in SETTING_NAMES:
        value = getattr(settings, name, None)
        if name == "MQTT_PORT":
            valid = (isinstance(value, int)
                     and not isinstance(value, bool)
                     and 1 <= value <= 65535)
        else:
            valid = isinstance(value, str) and bool(value.strip())
            if valid:
                text = value.strip().lower()
                valid = not (
                    text.startswith(("your-", "your_", "<"))
                    or text in ("changeme", "change-me", "replace-me",
                                "ssid", "password", "placeholder")
                )
        if not valid:
            errors.append("Edit %s in credentials.py." % name)
    return errors


def build_heartbeat(mac):
    """The topic identifies the robot; no name or category is needed."""
    return {
        "device_id": mac,
        "firmware": FIRMWARE_VERSION,
        "running": False,
        "run_id": None,
    }


def show_address(mac):
    print("+------------------------------------------+")
    print("Your robot's MAC address: %s" % mac)
    print("+------------------------------------------+")


def set_led(led, value):
    if led is not None:
        led.value(value)


def wifi_hint(status, network):
    """Use port constants: status numbers differ between boards."""
    if status == getattr(network, "STAT_WRONG_PASSWORD", -3):
        print("Wrong password: edit WIFI_PASSWORD.")
    elif status == getattr(network, "STAT_NO_AP_FOUND", -2):
        print("Network not found: check WIFI_SSID and range.")
        print("A 5 GHz-only network will not appear.")
    else:
        print("Wi-Fi failed: check the router and signal.")
    print("Pico needs 2.4 GHz Wi-Fi; check router settings.")


def connect_wifi(wlan, settings, network, time, led):
    """Try three times, allowing at most 20 seconds per attempt."""
    # Do not silently reuse a connection to somebody else's network.
    wlan.disconnect()
    for attempt in range(1, 4):
        print("Connecting Wi-Fi %d/3" % attempt, end="")
        start = time.ticks_ms()
        try:
            wlan.connect(settings.WIFI_SSID, settings.WIFI_PASSWORD)
            while not wlan.isconnected():
                if wlan.status() < 0:
                    break
                if time.ticks_diff(time.ticks_ms(), start) >= 20000:
                    break
                set_led(led, not led.value() if led else 0)
                print(".", end="")
                time.sleep_ms(500)
        except OSError:
            pass
        print()
        if wlan.isconnected():
            print("Wi-Fi OK")
            return True
        wifi_hint(wlan.status(), network)
        wlan.disconnect()
        if attempt < 3:
            time.sleep_ms(1000)
    print("Edit Wi-Fi settings, then run again.")
    return False


def register(client, mac, time):
    """PUBACK confirms broker delivery, not database registration."""
    status_topic = ("robosteam/robot/%s/status" % mac).encode()
    command_topic = ("robosteam/robot/%s/cmd" % mac).encode()
    answered = [False]
    pending = []

    def on_message(topic, message):
        if topic != command_topic:
            return
        try:
            data = json.loads(message)
        except (ValueError, TypeError):
            return
        if not isinstance(data, dict) or data.get("cmd") != "PING":
            return
        nonce = data.get("nonce")
        if not isinstance(nonce, str) or not nonce:
            return
        # A callback can run while publish() waits for PUBACK.
        # Queue replies to avoid nested QoS 1 packet handling.
        if len(pending) < 4:
            pending.append(nonce)

    def reply_to_pings():
        while pending:
            reply = build_heartbeat(mac)
            reply.update({"cmd": "PONG", "nonce": pending.pop(0)})
            client.publish(status_topic, json.dumps(reply).encode(), qos=1)
            answered[0] = True
            print("Website PING received; PONG sent.")

    client.set_callback(on_message)
    client.connect()  # umqtt.simple uses MQTT v3.1.1, plain TCP.
    client.subscribe(command_topic, qos=1)
    print("Broker connected.")
    payload = json.dumps(build_heartbeat(mac)).encode()
    for index in range(3):
        client.publish(status_topic, payload, qos=1, retain=False)
        print("Heartbeat %d/3 delivered to broker." % (index + 1))
        if index < 2:
            wait_for_commands(client, time, 2000, reply_to_pings)
    print("Heartbeats sent; no automatic server reply.")
    print("Listening for website Test connection (10 s).")
    wait_for_commands(client, time, 10000, reply_to_pings)
    return answered[0]


def wait_for_commands(client, time, duration, reply_to_pings):
    start = time.ticks_ms()
    while time.ticks_diff(time.ticks_ms(), start) < duration:
        client.check_msg()
        reply_to_pings()
        time.sleep_ms(100)


def show_summary(mac, answered):
    print("+------------------------------------------+")
    print("Wi-Fi OK")
    print("Server OK: broker received 3 heartbeats.")
    if answered:
        print("Website connection test answered.")
    else:
        print("Server registration: check on the website.")
    print("MAC: %s" % mac)
    print("https://competitions.robosteam.eu/")
    print("My Robots -> claim a robot -> paste this MAC.")
    print("Choose a name there; change it with Rename.")
    print("+------------------------------------------+")
    print("Done. Registration stays after this program ends.")
    print("Online status expires; use competition code to race.")


def run():
    print()
    print("RoboSTEAM - Register my robot")
    led = None
    client = None
    success = False
    try:
        import network
        import time
        from machine import Pin

        try:
            led = Pin("LED", Pin.OUT)
            led.value(0)
        except (ValueError, TypeError, OSError):
            pass  # The LED is helpful, but not required.
        wlan = network.WLAN(network.STA_IF)
        wlan.active(True)
        mac = format_mac(wlan.config("mac"))
        show_address(mac)

        try:
            import credentials
        except ImportError:
            print("Missing credentials.py on the Pico.")
            print("Copy credentials.py.example to credentials.py.")
            print("Edit WIFI_SSID and WIFI_PASSWORD there.")
            print("Ask the organiser for the MQTT settings.")
            return
        except SyntaxError:
            print("Check quotes and = signs in credentials.py.")
            return
        errors = validate_credentials(credentials)
        if errors:
            for error in errors:
                print(error)
            return

        try:
            from umqtt.simple import MQTTClient
        except ImportError:
            print("Missing umqtt.simple on this MicroPython build.")
            print("Ask your teacher to install umqtt.simple.")
            print("See the README, then run again.")
            return
        if not connect_wifi(wlan, credentials, network, time, led):
            return
        print("Connecting to the competition broker...")
        client = MQTTClient(
            client_id=mac.encode(), server=credentials.MQTT_BROKER,
            port=credentials.MQTT_PORT,
            user=credentials.MQTT_USER.encode(),
            password=credentials.MQTT_PASSWORD.encode(), keepalive=30,
        )
        try:
            answered = register(client, mac, time)
        except Exception:
            # Raw exceptions could contain private connection settings.
            print("Server connection or heartbeat failed.")
            print("Check MQTT_BROKER and MQTT_PORT.")
            print("Ask the organiser to check MQTT_USER/password.")
            print("Wi-Fi OK does not prove internet access.")
            print("Check internet on a phone on the same Wi-Fi.")
            print("Finish any venue sign-in, or use a hotspot.")
            print("The broker may also be offline or blocked.")
            print("Press Stop if waiting too long; then try again.")
            return
        show_summary(mac, answered)
        success = True
    except KeyboardInterrupt:
        print("Stopped. You can run this program again.")
    except Exception:
        print("Could not finish. Check Pico W MicroPython.")
        print("Check credentials.py, then run again.")
    finally:
        if client is not None:
            try:
                client.disconnect()
            except Exception:
                pass
        set_led(led, 1 if success else 0)


# Thonny runs as __main__; a normal Pico import also runs once.
# CPython imports leave hardware alone for the host-side tests.
import sys
if __name__ == "__main__" or sys.implementation.name == "micropython":
    run()
