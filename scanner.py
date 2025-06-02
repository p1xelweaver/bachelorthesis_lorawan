# Analyzing LoRa signal behaviour via moisture sensor monitoring

#   Program startup tasks:
#   1. Connect LoRa Stick to LoRa gateway via OTAA
#       1.1 Set default settings (e.g. Spreading factor...)
#       1.2 Use credentials: App EUI, App Key, Device EUI
#   2. Connect to moisture sensor via USB2Serial adapter
#       2.1 Read moisture and temperature from sensor
#       2.2 Put data into local file and into LoRa payload
#           2.2.1 Data: moisture, temperature, LoRa signal strength statistics
#       2.3 Send payload to TTN via LoRa stick
#       2.4 Repeat step 2.1 - 2.3 on a regular intervall

# imports
import os
import time
import json
import serial
import chirp_modbus
from enum import IntEnum
from serial.threaded import LineReader, ReaderThread
from datetime import datetime

# constants
OTAA_RETRIES = 10
PORT_LOSTIK = ""

# LoRa/LoStick variables
appeui = ""     # App EUI
appkey = ""     # App Key
deveui = ""     # Device EUI

appskey = ""    # App Session Key
nwkskey = ""    # Network Session Key
devaddr = ""    # Device Address

# moisture sensor variables
runs = 10           # No. of uplink messages
ul_interval = 600   # Interval for sending uplink messages in seconds
dl_interval = 600   # Interval for sending downlink messages in seconds
adapt_int = 0       # Flag if send Interval should be decreased

# find LoStick in devices
for i in range(0, 3):
    tmp = os.system("ls /dev/ttyUSB" + str(i))
    if tmp == 0:
        PORT_LOSTIK = "/dev/ttyUSB" + str(i)
        break

#### classes for LoStick connection handling START ####
class MaxRetriesError(Exception):
    pass

class ConnectionState(IntEnum):
    SUCCESS = 0
    CONNECTING = 100
    CONNECTED = 200
    FAILED = 500
    TO_MANY_RETRIES = 520

class PrintLines(LineReader):
    retries = 0
    state = ConnectionState.CONNECTING

    def retry(self, action):
        if self.retries >= OTAA_RETRIES:
            print("Too many retries, exiting")
            self.state = ConnectionState.TO_MANY_RETRIES
            return
        self.retries = self.retries + 1
        action()

    def get_var(self, cmd):
        self.send_cmd(cmd)
        return self.transport.serial.readline()

    def join(self):
        self.join_otaa()

    def join_otaa(self):
        """
        join method - before joining set dr to 5 for optimally reaching gateway and adr to on
        """
        self.send_cmd('mac set dr 5')
        time.sleep(1)
        self.send_cmd('mac set adr on')
        time.sleep(1)
        self.send_cmd('mac set appeui %s' % appeui)
        time.sleep(1)
        self.send_cmd('mac set appkey %s' % appkey)
        time.sleep(1)
        self.send_cmd('mac set deveui %s' % deveui)
        time.sleep(1)
        self.send_cmd('mac save')
        time.sleep(1)
        self.send_cmd('mac join otaa')

    def connection_made(self, transport):
        """
        Fires when connection is made to serial port device
        """
        print("Connection to LoStik established")
        self.transport = transport
        self.retry(self.join)

    def handle_line(self, data):
        """
        method for getting otaa result
        """
        print("STATUS: %s" % data)
        if data.strip() == "denied" or data.strip() == "no_free_ch":
            print("Retrying OTAA connection")
            self.retry(self.join)
        elif data.strip() == "accepted":
            print("UPDATING STATE to connected")
            self.state = ConnectionState.CONNECTED
            exit(protocol.state)

    def connection_lost(self, exc):
        """
        Called when serial connection is severed to device
        """
        if exc:
            print(exc)
        print("Lost connection to serial device")

    def send_cmd(self, cmd, delay=.5):
        print(cmd)
        self.transport.write(('%s\r\n' % cmd).encode('UTF-8'))
        time.sleep(delay)
        
#### classes for LoStick connection handling END ####

#### main program START ####

ser = serial.Serial(PORT_LOSTIK, baudrate=57600) # establish connection with LoStick
sensor = chirp_modbus.SoilMoistureSensor(address=1, serialport='/dev/ttyUSB1')
with ReaderThread(ser, PrintLines) as protocol:
    i = 0
    while protocol.state != ConnectionState.CONNECTED and i < OTAA_RETRIES:
        print("Not yet connected")
        time.sleep(10)
        i += 1
        continue
print(protocol.state)
exit(protocol.state)

#### main program END ####

