"""Host checks: python -m unittest discover -s tests -v"""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

import register_robot as robot


def settings(**overrides):
    # Fictional test values; never connect to a real network.
    values = dict(WIFI_SSID="test-network", WIFI_PASSWORD="test-only",
                  MQTT_BROKER="broker.invalid", MQTT_PORT=1883,
                  MQTT_USER="test-user", MQTT_PASSWORD="test-secret")
    values.update(overrides)
    return types.SimpleNamespace(**values)


class FakeTime:
    def __init__(self):
        self.now = 0

    def ticks_ms(self):
        return self.now

    def ticks_diff(self, end, start):
        return end - start

    def sleep_ms(self, delay):
        self.now += delay


class FakeWLAN:
    def __init__(self, status=3):
        self.result = status
        self.connected = False
        self.attempts = 0

    def active(self, value):
        pass

    def config(self, name):
        return bytes.fromhex("aabbccddeeff")

    def disconnect(self):
        self.connected = False

    def connect(self, ssid, password):
        self.attempts += 1
        self.connected = self.result == 3

    def isconnected(self):
        return self.connected

    def status(self):
        return self.result


class FakeClient:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.published = []
        self.incoming = []
        self.disconnected = False
        self.publishing = False

    def set_callback(self, callback):
        self.callback = callback

    def connect(self):
        self.connected = True

    def subscribe(self, topic, qos):
        self.subscription = (topic, qos)

    def publish(self, topic, payload, qos, retain=False):
        if self.publishing:
            raise AssertionError("Nested QoS 1 publish")
        self.publishing = True
        self.published.append((topic, json.loads(payload), qos, retain))
        if self.incoming:
            self.callback(*self.incoming.pop(0))
        self.publishing = False

    def check_msg(self):
        if self.incoming:
            self.callback(*self.incoming.pop(0))

    def disconnect(self):
        self.disconnected = True


class FakePin:
    OUT = 1

    def __init__(self, *args):
        self.state = 0

    def value(self, state=None):
        if state is not None:
            self.state = state
        return self.state


class RegistrationTests(unittest.TestCase):
    def setUp(self):
        self.output = io.StringIO()
        self.capture = contextlib.redirect_stdout(self.output)
        self.capture.__enter__()
        self.addCleanup(self.capture.__exit__, None, None, None)
        self.mac = "AA:BB:CC:DD:EE:FF"
        self.network = types.SimpleNamespace(
            STA_IF=0, STAT_WRONG_PASSWORD=-3, STAT_NO_AP_FOUND=-2)

    def test_mac_includes_leading_zeroes_and_uppercase(self):
        self.assertEqual(robot.format_mac(b"\x00\x01\x0a\xbb\xfe\xff"),
                         "00:01:0A:BB:FE:FF")

    def test_mac_requires_six_bytes(self):
        with self.assertRaises(ValueError):
            robot.format_mac(b"short")

    def test_valid_settings(self):
        self.assertEqual(robot.validate_credentials(settings()), [])

    def test_missing_settings_name_exact_lines(self):
        errors = robot.validate_credentials(types.SimpleNamespace())
        self.assertEqual(len(errors), 6)
        for name, error in zip(robot.SETTING_NAMES, errors):
            self.assertEqual(error, "Edit %s in credentials.py." % name)

    def test_example_requires_connection_values(self):
        path = Path(__file__).resolve().parents[1] / "credentials.py.example"
        example = types.ModuleType("example")
        exec(compile(path.read_text(), str(path), "exec"), example.__dict__)
        errors = robot.validate_credentials(example)
        self.assertEqual(len(errors), 5)
        self.assertTrue(any("MQTT_BROKER" in e for e in errors))

    def test_placeholder_and_empty_strings(self):
        for value in (None, "", "  ", "your-wifi-name", "<password>",
                      "CHANGEME", "placeholder", 123):
            with self.subTest(value=value):
                errors = robot.validate_credentials(
                    settings(WIFI_PASSWORD=value))
                self.assertEqual(errors,
                                 ["Edit WIFI_PASSWORD in credentials.py."])

    def test_port_range_and_type(self):
        for value in (0, 65536, "1883", True, None):
            self.assertEqual(robot.validate_credentials(
                settings(MQTT_PORT=value)),
                ["Edit MQTT_PORT in credentials.py."])
        for value in (1, 1883, 51884, 65535):
            self.assertEqual(robot.validate_credentials(
                settings(MQTT_PORT=value)), [])

    def test_payload_has_no_name_category_or_timestamp(self):
        payload = robot.build_heartbeat(self.mac)
        self.assertEqual(payload, {
            "device_id": self.mac, "firmware": robot.FIRMWARE_VERSION,
            "running": False, "run_id": None,
        })
        self.assertEqual(json.loads(json.dumps(payload)), payload)

    def test_wifi_success(self):
        wlan = FakeWLAN()
        self.assertTrue(robot.connect_wifi(
            wlan, settings(), self.network, FakeTime(), FakePin()))
        self.assertEqual(wlan.attempts, 1)

    def test_wifi_failure_hints_and_three_attempts(self):
        for status, hint in ((-3, "Wrong password"),
                             (-2, "Network not found"),
                             (-1, "check the router")):
            with self.subTest(status=status):
                wlan = FakeWLAN(status)
                self.assertFalse(robot.connect_wifi(
                    wlan, settings(), self.network, FakeTime(), None))
                self.assertEqual(wlan.attempts, 3)
                self.assertIn(hint, self.output.getvalue())
        self.assertIn("5 GHz-only", self.output.getvalue())
        self.assertIn("2.4 GHz", self.output.getvalue())

    def test_wifi_timeout_is_twenty_seconds_per_attempt(self):
        clock = FakeTime()
        wlan = FakeWLAN(1)
        self.assertFalse(robot.connect_wifi(
            wlan, settings(), self.network, clock, None))
        self.assertEqual(clock.now, 62000)  # 3 x 20 s + two 1 s gaps
        self.assertEqual(wlan.attempts, 3)
        self.assertTrue(all(len(line) <= 60
                            for line in self.output.getvalue().splitlines()))

    def test_three_qos_one_heartbeats_and_honest_fallback(self):
        client = FakeClient()
        clock = FakeTime()
        self.assertFalse(robot.register(client, self.mac, clock))
        self.assertEqual(client.subscription,
                         (b"robosteam/robot/AA:BB:CC:DD:EE:FF/cmd", 1))
        self.assertEqual(len(client.published), 3)
        for topic, payload, qos, retain in client.published:
            self.assertEqual(topic,
                             b"robosteam/robot/AA:BB:CC:DD:EE:FF/status")
            self.assertEqual(payload, robot.build_heartbeat(self.mac))
            self.assertEqual(qos, 1)
            self.assertFalse(retain)
        self.assertEqual(clock.now, 14000)
        self.assertIn("no automatic server reply", self.output.getvalue())
        self.assertNotIn("robot registered", self.output.getvalue())

    def test_ping_during_publish_is_queued_and_nonce_echoed(self):
        client = FakeClient()
        client.incoming = [(
            b"robosteam/robot/AA:BB:CC:DD:EE:FF/cmd",
            b'{"cmd":"PING","nonce":"test-nonce"}')]
        self.assertTrue(robot.register(client, self.mac, FakeTime()))
        pongs = [p for p in client.published if p[1].get("cmd") == "PONG"]
        self.assertEqual(len(pongs), 1)
        self.assertEqual(pongs[0][1]["nonce"], "test-nonce")
        self.assertEqual(pongs[0][2], 1)

    def test_ignores_malformed_unrelated_and_motor_commands(self):
        client = FakeClient()
        topic = b"robosteam/robot/AA:BB:CC:DD:EE:FF/cmd"
        client.incoming = [(topic, payload) for payload in (
            b"broken", b"[]", b"null", b'{"cmd":"START"}',
            b'{"cmd":"STOP"}', b'{"cmd":"PING"}',
            b'{"cmd":"PING","nonce":4}')]
        client.incoming.append((b"another/topic",
                                b'{"cmd":"PING","nonce":"ignored"}'))
        self.assertFalse(robot.register(client, self.mac, FakeTime()))
        self.assertEqual(len(client.published), 3)

    def run_with_fakes(self, client, credentials=None, overrides=None,
                       invoke=None):
        network = types.ModuleType("network")
        network.STA_IF = 0
        network.WLAN = lambda interface: FakeWLAN()
        machine = types.ModuleType("machine")
        machine.Pin = FakePin
        mqtt = types.ModuleType("umqtt.simple")
        mqtt.MQTTClient = lambda **kwargs: (
            setattr(client, "kwargs", kwargs) or client)
        modules = {"network": network, "machine": machine,
                   "time": FakeTime(), "umqtt": types.ModuleType("umqtt"),
                   "umqtt.simple": mqtt,
                   "credentials": credentials or settings()}
        modules.update(overrides or {})
        with patch.dict(sys.modules, modules):
            (invoke or robot.run)()

    def test_complete_run_with_fake_hardware(self):
        client = FakeClient()
        self.run_with_fakes(client)
        self.assertEqual(client.kwargs["client_id"], self.mac.encode())
        self.assertEqual(client.kwargs["port"], 1883)
        self.assertTrue(client.disconnected)
        output = self.output.getvalue()
        self.assertIn("My Robots -> claim a robot", output)
        self.assertIn("Server registration: check on the website.", output)
        self.assertNotIn("test-secret", output)
        self.assertNotIn("test-only", output)
        self.assertTrue(all(len(line) <= 60 for line in output.splitlines()))

    def test_readme_transcript_matches_complete_run(self):
        self.run_with_fakes(FakeClient())
        path = Path(__file__).resolve().parents[1] / "README.md"
        transcript = path.read_text(encoding="utf-8").split("```text\n")[1]
        transcript = transcript.split("```", 1)[0]
        self.assertEqual(self.output.getvalue(), transcript)

    def test_normal_import_on_micropython_runs_once(self):
        source = Path(robot.__file__).read_text(encoding="utf-8")
        fake_sys = types.ModuleType("sys")
        fake_sys.implementation = types.SimpleNamespace(name="micropython")
        namespace = {"__name__": "register_robot"}
        def import_on_pico():
            exec(compile(source, "register_robot.py", "exec"), namespace)
        client = FakeClient()
        self.run_with_fakes(client, overrides={"sys": fake_sys},
                            invoke=import_on_pico)
        self.assertEqual(len(client.published), 3)
        self.assertIn("RoboSTEAM - Register my robot", self.output.getvalue())

    def test_missing_credentials_gives_filename_and_settings(self):
        self.run_with_fakes(FakeClient(), overrides={"credentials": None})
        self.assertIn("Missing credentials.py on the Pico.",
                      self.output.getvalue())
        self.assertIn("Edit WIFI_SSID and WIFI_PASSWORD there.",
                      self.output.getvalue())
        self.assertNotIn("Wi-Fi OK", self.output.getvalue())

    def test_missing_mqtt_explains_install(self):
        self.run_with_fakes(FakeClient(), overrides={"umqtt.simple": None})
        self.assertIn("Missing umqtt.simple", self.output.getvalue())
        self.assertNotIn("Server OK:", self.output.getvalue())

    def test_failed_second_heartbeat_cannot_report_success(self):
        client = FakeClient()
        publish = client.publish
        def fail_second(*args, **kwargs):
            if client.published:
                raise OSError("test-secret")
            publish(*args, **kwargs)
        client.publish = fail_second
        self.run_with_fakes(client)
        self.assertNotIn("Server OK:", self.output.getvalue())
        self.assertNotIn("test-secret", self.output.getvalue())
        self.assertTrue(client.disconnected)

    def test_keyboard_interrupt_cleans_up(self):
        client = FakeClient()
        def interrupt():
            raise KeyboardInterrupt()
        client.connect = interrupt
        self.run_with_fakes(client)
        self.assertIn("Stopped.", self.output.getvalue())
        self.assertNotIn("Server OK:", self.output.getvalue())
        self.assertTrue(client.disconnected)

    def test_failure_does_not_print_exception_secrets_or_success(self):
        client = FakeClient()
        def fail():
            raise OSError("test-secret test-only")
        client.connect = fail
        self.run_with_fakes(client)
        output = self.output.getvalue()
        self.assertNotIn("test-secret", output)
        self.assertNotIn("test-only", output)
        self.assertNotIn("Server OK:", output)
        self.assertIn("Check internet on a phone", output)
        self.assertTrue(client.disconnected)

    def test_import_on_pc_does_not_use_hardware(self):
        path = Path(robot.__file__)
        spec = importlib.util.spec_from_file_location("host_import", path)
        module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"network": None, "machine": None,
                                      "umqtt": None}):
            spec.loader.exec_module(module)
        self.assertEqual(self.output.getvalue(), "")


if __name__ == "__main__":
    unittest.main()
