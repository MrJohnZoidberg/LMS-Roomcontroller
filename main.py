#!/usr/bin/python3

import toml
import json
import paho.mqtt.client as mqtt
import bluetoothctl
import snapcastctl
import mpdctl

MQTT_BROKER_ADDRESS = "localhost:1883"
MQTT_USERNAME = None
MQTT_PASSWORD = None


def send_site_info(client=None, userdata=None, msg=None):
    client.publish('bluetooth/answer/siteInfo', payload=json.dumps({'room_name': room_name, 'site_id': site_id}))


def on_connect(client, userdata, flags, rc):
    client.message_callback_add(f'bluetooth/request/oneSite/{site_id}/devicesDiscover', bltctl.discover)
    client.message_callback_add(f'bluetooth/request/oneSite/{site_id}/deviceConnect', bltctl.connect)
    client.message_callback_add(f'bluetooth/request/oneSite/{site_id}/deviceDisconnect', bltctl.disconnect)
    client.message_callback_add(f'bluetooth/request/oneSite/{site_id}/deviceRemove', bltctl.remove)
    client.message_callback_add(f'bluetooth/request/oneSite/{site_id}/deviceLists', bltctl.send_device_lists)
    client.message_callback_add(f'bluetooth/request/oneSite/{site_id}/siteInfo', send_site_info)
    client.message_callback_add('bluetooth/request/allSites/deviceLists', bltctl.send_device_lists)
    client.message_callback_add('bluetooth/request/allSites/siteInfo', send_site_info)
    client.subscribe(f'bluetooth/request/oneSite/{site_id}/#')
    client.subscribe('bluetooth/request/allSites/#')

    client.message_callback_add(f'snapclient/{site_id}/startService', sncctl.start)
    client.message_callback_add(f'snapclient/{site_id}/stopService', sncctl.stop)
    client.subscribe(f'snapclient/{site_id}/#')


if __name__ == "__main__":
    config = toml.load('config.toml')
    if 'mqtt' in config['snips-common']:
        MQTT_BROKER_ADDRESS = config['snips-common']['mqtt']
    if 'mqtt_username' in config['snips-common']:
        MQTT_USERNAME = config['snips-common']['mqtt_username']
    if 'mqtt_password' in config['snips-common']:
        MQTT_PASSWORD = config['snips-common']['mqtt_password']
    site_id = config['device']['site_id']
    room_name = config['device']['room_name']

    mqtt_client = mqtt.Client()
    mqtt_client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    mqtt_client.on_connect = on_connect
    mqtt_client.connect(MQTT_BROKER_ADDRESS.split(":")[0], int(MQTT_BROKER_ADDRESS.split(":")[1]))

    bltctl = bluetoothctl.Bluetooth(mqtt_client, config)
    bltctl.send_device_lists()
    sncctl = snapcastctl.SnapcastControll()
    mpdctl = mpdctl.MPDControll()

    send_site_info()
    mqtt_client.loop_forever()
