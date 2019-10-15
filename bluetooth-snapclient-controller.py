#!/usr/bin/python3

import paho.mqtt.client as mqtt
import json
import toml
import threading
import blctl
import time

MQTT_BROKER_ADDRESS = "localhost:1883"
MQTT_USERNAME = None
MQTT_PASSWORD = None


class Snapclient:
    def __init__(self):
        pass


class Bluetooth:
    def __init__(self):
        self.threadobj_discover = None
        self.threadobj_connect = None
        self.threadobj_disconnect = None
        self.threadobj_remove = None
        self.ctl = blctl.Bluetoothctl()

    def thread_discover(self):
        result = self.ctl.start_discover()
        payload = {'siteId': site_id, 'result': result}
        mqtt_client.publish(f'bluetooth/result/{site_id}/devicesDiscover', payload=json.dumps(payload))
        if not result:
            return
        for i in range(30):
            time.sleep(1)
        self.send_device_lists()
        payload = {'discoverable_devices': self.ctl.get_discoverable_devices(),
                   'siteId': site_id}
        mqtt_client.publish(f'bluetooth/result/{site_id}/devicesDiscovered', payload=json.dumps(payload))

    def thread_connect(self, addr):
        print("Started")
        result = self.ctl.connect(addr)
        if result:
            self.send_device_lists()
        payload = {'siteId': site_id, 'result': result, 'addr': addr}
        mqtt_client.publish(f'bluetooth/result/{site_id}/deviceConnect', payload=json.dumps(payload))

    def discover(self, client, userdata, msg):
        if self.threadobj_discover:
            del self.threadobj_discover
        self.threadobj_discover = threading.Thread(target=self.thread_discover)
        self.threadobj_discover.start()

    def connect(self, client, userdata, msg):
        data = json.loads(msg.payload.decode("utf-8"))
        if self.threadobj_connect:
            del self.threadobj_connect
        self.threadobj_connect = threading.Thread(target=self.thread_connect, args=(data['addr'],))
        self.threadobj_connect.start()

    def send_device_lists(self, client=None, userdata=None, msg=None):
        payload = {'available_devices': self.ctl.get_available_devices(),
                   'paired_devices': self.ctl.get_paired_devices(),
                   'siteId': site_id}
        print(payload)
        mqtt_client.publish('bluetooth/update/deviceLists', payload=json.dumps(payload))


def on_connect(client, userdata, flags, rc):
    client.message_callback_add(f'bluetooth/ask/{site_id}/devicesDiscover', bl.discover)
    client.message_callback_add(f'bluetooth/ask/{site_id}/deviceConnect', bl.connect)
    client.message_callback_add('bluetooth/update/requestDeviceLists', bl.send_device_lists)
    client.subscribe(f'bluetooth/ask/{site_id}/devicesDiscover')
    client.subscribe(f'bluetooth/ask/{site_id}/deviceConnect')
    client.subscribe('bluetooth/update/requestDeviceLists')
    bl.send_device_lists()


if __name__ == "__main__":
    config = toml.load('config.toml')
    if 'mqtt' in config['snips-common']:
        MQTT_BROKER_ADDRESS = config['snips-common']['mqtt']
    if 'mqtt_username' in config['snips-common']:
        MQTT_USERNAME = config['snips-common']['mqtt_username']
    if 'mqtt_password' in config['snips-common']:
        MQTT_PASSWORD = config['snips-common']['mqtt_password']
    site_id = config['device']['site_id']

    bl = Bluetooth()

    mqtt_client = mqtt.Client()
    mqtt_client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    mqtt_client.on_connect = on_connect
    mqtt_client.connect(MQTT_BROKER_ADDRESS.split(":")[0], int(MQTT_BROKER_ADDRESS.split(":")[1]))
    mqtt_client.loop_forever()
