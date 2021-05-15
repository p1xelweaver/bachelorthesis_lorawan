##!/usr/bin/env python
## adapted from https://github.com/ronoth/LoStik
# script to monitor capacitivie moisture sensor from chirp
# Author Gudrun Huszar
# Jan. 2021


import sys
import time
import argparse
from enum import IntEnum
import serial
from serial.threaded import LineReader, ReaderThread
import json
from influxdb import InfluxDBClient
import chirp_modbus
from datetime import datetime

sensor = chirp_modbus.SoilMoistureSensor(address=1, serialport='/dev/ttyUSB1')

parser = argparse.ArgumentParser(description='Connect to LoRaWAN network')

parser.add_argument('--runs', help="No. of uplink messages", default="10")
parser.add_argument('--ul_interval', help="Interval for sending uplink messages in seconds", default="600")
parser.add_argument('--dl_interval', help="Interval for sending downlink messages in seconds", default="600")
parser.add_argument('--adapt_int', help="Flag if send Interval should be decreased", default="0")
parser.add_argument('--deveui', help='Device EUI', default="")
parser.add_argument('--db_host', help='Database Host', default="localhost")
parser.add_argument('--db_name', help='Database Name', default="lostik")

args = parser.parse_args()

OTAA_RETRIES = 5

PORT = ""
fields = {}
tags = {}
output = {}
tags['devEUI'] = args.deveui
MEASUREMENT = []

# set up data base connection
DB_HOST = args.db_host
DB_NAME = args.db_name

client = InfluxDBClient(host=DB_HOST, port=8086)
client.create_database(DB_NAME)
client.get_list_database()
client.switch_database(DB_NAME)


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
    state = ConnectionState.CONNECTED

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

    def connection_made(self, transport):
        """
        Fires when connection is made to serial port device
        """
        print("Connection to LoStik established")
        self.transport = transport

    def handle_line(self, data):
        """
            method for getting otaa result
        """
        # if data == "ok" or data == 'busy':
        #     return
        if data == "no_free_ch":
            sys.stdout.write("No free Channel")
        sys.stdout.write(" %s, " % data)
        try:
            data = float(data)
        except ValueError:
            pass
        MEASUREMENT.append(data)
        if len(MEASUREMENT) > 1:
            self._prepare_json()

    def connection_lost(self, exc):
        """
        Called when serial connection is severed to device
        """
        if exc:
            print(exc)
        print("Lost connection to serial device")

    def send_cmd(self, cmd, delay=.5):
        sys.stdout.write(cmd)
        self.transport.write(('%s\r\n' % cmd).encode('UTF-8'))
        time.sleep(delay)

    @staticmethod
    def _prepare_json():
        """method to prepare data in json format for db"""
        fields[MEASUREMENT[0]] = MEASUREMENT[1]
        del MEASUREMENT[:]


ser = serial.Serial("/dev/ttyUSB0", baudrate=57600)
# set measurement configuration
no_of_runs = args.runs
ul_interval = args.ul_interval
dl_interval = args.dl_interval
adapt_int = args.adapt_int
with ReaderThread(ser, PrintLines) as protocol:
    # set linkCheckReq Interval for receiving downlink messages
    protocol.send_cmd("mac set linkchk %s" % dl_interval)
    j = 0
    # performing measurements and store them in the fields array for json dump
    for i in range(int(no_of_runs)):
        print(" ")
        moisture = sensor.getMoisture()
        temperature = sensor.getTemperature()
        payload = "%04d" % moisture + "%04d" % temperature
        print(payload)

        output['measurement'] = 'LoStik'
        time_log = datetime.isoformat(datetime.now())
        output['time'] = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
        sys.stdout.write("%s, " % time_log)

        MEASUREMENT.append('frequency')
        protocol.send_cmd("radio get freq")

        MEASUREMENT.append('bandwidth')
        protocol.send_cmd("radio get bw")

        MEASUREMENT.append('rssi')
        protocol.send_cmd("radio get rssi")

        MEASUREMENT.append('snr')
        protocol.send_cmd("radio get snr")

        MEASUREMENT.append('data rate')
        protocol.send_cmd("mac get dr")

        MEASUREMENT.append('gateways')
        protocol.send_cmd("mac get gwnb")

        MEASUREMENT.append('power')
        protocol.send_cmd("mac get pwridx")

        MEASUREMENT.append('mrgn')
        protocol.send_cmd("mac get mrgn")

        # store the internal frame counter
        fields['frames'] = str(i)

        # send unconfirmed uplink message
        protocol.send_cmd("mac tx uncnf 1 %d" % i)

        output['tags'] = tags
        output['fields'] = fields

        # write data
        influx_json = json.dumps(output)
        client.write_points([output])

        # wait for sending next uplink message
        time.sleep(float(ul_interval))
        sys.stdout.flush()
        # tranmission interval experiments
        if adapt_int is "1" and j < 10:
            if int(ul_interval) < 60:
                ul_interval = 0
            else:
                ul_interval = str(int(ul_interval) - 30)
                dl_interval = str(int(dl_interval) - 30)
                # adapt downlink time
                protocol.send_cmd("mac set linkchk %s" % dl_interval)
        if j < 10:
            j += 1
        else:
            j = 0
    exit(protocol.state)
