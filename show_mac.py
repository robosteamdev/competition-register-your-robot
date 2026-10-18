"""Only display the MAC: no Wi-Fi login and no motor commands."""
import network

wlan = network.WLAN(network.STA_IF)
wlan.active(True)
mac = ":".join("%02X" % part for part in wlan.config("mac"))

print()
print("+------------------------------------------+")
print("Your robot's MAC address: %s" % mac)
print("+------------------------------------------+")
print("My Robots -> claim a robot -> paste this MAC.")
print("Write the MAC on a sticker for your robot.")
