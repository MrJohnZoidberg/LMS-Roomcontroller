#!/usr/bin/python3

import toml
import paho.mqtt.client as mqtt
import bluetoothctl
import snapclientctl

MQTT_BROKER_ADDRESS = "localhost:1883"
MQTT_USERNAME = None
MQTT_PASSWORD = None


def on_connect(client, userdata, flags, rc):
    client.message_callback_add(f'bluetooth/request/oneSite/{site_id}/devicesDiscover', bl.discover)
    client.message_callback_add(f'bluetooth/request/oneSite/{site_id}/deviceConnect', bl.connect)
    client.message_callback_add(f'bluetooth/request/oneSite/{site_id}/deviceDisconnect', bl.disconnect)
    client.message_callback_add(f'bluetooth/request/oneSite/{site_id}/deviceRemove', bl.remove)
    client.message_callback_add(f'bluetooth/request/oneSite/{site_id}/deviceLists', bl.send_device_lists)
    client.message_callback_add(f'bluetooth/request/oneSite/{site_id}/siteInfo', bl.send_site_info)
    client.message_callback_add('bluetooth/request/allSites/deviceLists', bl.send_device_lists)
    client.message_callback_add('bluetooth/request/allSites/siteInfo', bl.send_site_info)
    client.subscribe(f'bluetooth/request/oneSite/{site_id}/#')
    client.subscribe('bluetooth/request/allSites/#')

    client.message_callback_add(f'snapclient/{site_id}/startService', snapclientctl.start)
    client.message_callback_add(f'snapclient/{site_id}/stopService', snapclientctl.stop)
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

    mqtt_client = mqtt.Client()
    mqtt_client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    mqtt_client.on_connect = on_connect
    mqtt_client.connect(MQTT_BROKER_ADDRESS.split(":")[0], int(MQTT_BROKER_ADDRESS.split(":")[1]))

    bl = bluetoothctl.Bluetooth(mqtt_client, config)
    bl.send_site_info()
    bl.send_device_lists()
    snapclientctl = snapclientctl.SnapclientControll()

    mqtt_client.loop_forever()
