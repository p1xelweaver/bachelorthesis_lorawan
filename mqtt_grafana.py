# https://www.thethingsnetwork.org/forum/t/a-python-program-to-listen-to-your-devices-with-mqtt/9036/6
# Get data from MQTT server
# Run this with python 3, install paho.mqtt prior to use
# adapted by: Gudrun Huszar
# Jan. 2021

import paho.mqtt.client as mqtt
from datetime import datetime
import json
from influxdb import InfluxDBClient
import argparse
import sys

MEASUREMENT = []
STATE = -1

parser = argparse.ArgumentParser(description='Connect to TTN via MQTT')

parser.add_argument('--appid', help="Application id", default="")
parser.add_argument('--accesskey' , help="Access Key", default="")
parser.add_argument('--deveui', help='Device EUI', default="")
parser.add_argument('--db_host', help='Database Host', default="localhost")
parser.add_argument('--db_name', help='Database Name', default="lostik")

args = parser.parse_args()


#set up data base connection
APPID = args.appid
ACCESSKEY = args.accesskey
DB_HOST = args.db_host
DB_NAME = args.db_name

data = []
fields = {}
tags = {}
output = {}
tags['devEUI'] = args.deveui
client = InfluxDBClient(host=DB_HOST, port=8086)
client.get_list_database()
client.switch_database(DB_NAME)


def on_connect(mqttc, mosq, obj, rc):
    """
    method to get connection message
    """
    print("Connected with result code:"+str(rc))
    # subscribe for all devices of user
    mqttc.subscribe('+/devices/+/up')
    mqttc.subscribe('+/devices/+/events/down/sent')
    if rc != 0:
        sys.exit('Could not connect to server. \n Result code: ' + str(rc))


def on_message(mqttc,obj,msg):
    """
    method to get message from device
    """
    gateways = []
    output['measurement'] = 'LoStick'
    output['time'] = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    try:
        x = json.loads(msg.payload.decode('utf-8'))
        if "up" in msg._topic.decode("utf-8"):
            airtime = x["metadata"]["airtime"]
            gateways = x["metadata"]["gateways"]
            fields["airtimeUL"] = airtime
            output['fields'] = fields
        elif "down" in msg._topic.decode("utf-8"):
            airtime = x["config"]["airtime"]
            fields["airtimeDL"] = airtime
        if len(gateways) > 1:
            rssi = 0
            for gw in gateways:
                rssi += gw["rssi"]
            rssi /= len(gateways)
            fields["gw_rssi"] = rssi
        print("outpout: ", output)
        output['tags'] = tags
        output['fields'] = fields
        client.write_points([output])
        sys.stdout.flush()
    except Exception as e:
        print(e)
        pass


def on_publish(mosq, obj, mid):
    print("mid: " + str(mid))


def on_subscribe(mosq, obj, mid, granted_qos):
    print("Subscribed: " + str(mid) + " " + str(granted_qos))


def on_log(mqttc,obj,level,buf):
    print("message:" + str(buf))
    print("userdata:" + str(obj))


mqttc = mqtt.Client()
# Assign event callbacks
mqttc.on_connect = on_connect
mqttc.on_message = on_message

mqttc.username_pw_set(APPID, ACCESSKEY)
mqttc.connect("eu.thethings.network", 1883, 60)

# listen to server
run = True
while run:
    mqttc.loop_forever()
