##!/usr/bin/env python3
## adapted from https://github.com/ronoth/LoStik
import time
import argparse
from enum import IntEnum
import serial
from serial.threaded import LineReader, ReaderThread
import os

# Parser
parser = argparse.ArgumentParser(description='Connect to LoRaWAN network')
parser.add_argument('--joinmode', '-j', help="otaa, abp", default="otaa")

# ABP credentials
parser.add_argument('--appskey', help="App Session Key", default="")
parser.add_argument('--nwkskey', help="Network Session Key", default="")
parser.add_argument('--devaddr', help="Device Address", default="")

# OTAA credentials
parser.add_argument('--appeui', help="App EUI", default="")
parser.add_argument('--appkey', help="App Key", default="")
parser.add_argument('--deveui', help="Device EUI", default="")

args = parser.parse_args()

# retries for otaa connection
OTAA_RETRIES = 5
PORT = ""

# find Lostik on USB port
for i in range(0, 3):
    tmp = os.system("ls /dev/ttyUSB" + str(i))
    if tmp == 0:
        PORT = "/dev/ttyUSB" + str(i)
        break


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
        if (self.retries >= OTAA_RETRIES):
            print("Too many retries, exiting")
            self.state = ConnectionState.TO_MANY_RETRIES
            return
        self.retries = self.retries + 1
        action()

    def get_var(self, cmd):
        self.send_cmd(cmd)
        return self.transport.serial.readline()

    def join(self):
        # TODO maybe delete abp
        if args.joinmode == "abp":
            self.join_abp()
        else:
            self.join_otaa()

    # join method - before joining set dr to 5 for optimally reaching gateway and adr to on
    def join_otaa(self):
        self.send_cmd('mac set dr 5')
        time.sleep(1)
        self.send_cmd('mac set adr on')
        time.sleep(1)
        self.send_cmd('mac set appeui %s' % args.appeui)
        time.sleep(1)
        self.send_cmd('mac set appkey %s' % args.appkey)
        time.sleep(1)
        self.send_cmd('mac set deveui %s' % args.deveui)
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

    # method for getting otaa result
    def handle_line(self, data):
        print("STATUS: %s" % data)
        if data.strip() == "denied" or data.strip() == "no_free_ch":
            print("Retrying OTAA connection")
        #           self.retry(self.join)
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


ser = serial.Serial(PORT, baudrate=57600)
with ReaderThread(ser, PrintLines) as protocol:
    i = 0
    while protocol.state != ConnectionState.CONNECTED and i < OTAA_RETRIES:
        print("Not yet connected")
        time.sleep(10)
        i += 1
        continue
print(protocol.state)
exit(protocol.state)
