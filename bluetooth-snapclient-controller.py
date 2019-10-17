#!/usr/bin/python3

import paho.mqtt.client as mqtt
import toml
import bluetoothctl
import snapclientctl

MQTT_BROKER_ADDRESS = "localhost:1883"
MQTT_USERNAME = None
MQTT_PASSWORD = None


def on_connect(client, userdata, flags, rc):
    client.message_callback_add(f'bluetooth/ask/{site_id}/devicesDiscover', bl.discover)
    client.message_callback_add(f'bluetooth/ask/{site_id}/deviceConnect', bl.connect)
    client.message_callback_add(f'bluetooth/ask/{site_id}/deviceDisconnect', bl.disconnect)
    client.message_callback_add(f'bluetooth/ask/{site_id}/deviceTrust', bl.trust)
    client.message_callback_add(f'bluetooth/ask/{site_id}/deviceUntrust', bl.untrust)
    client.message_callback_add(f'bluetooth/ask/{site_id}/deviceRemove', bl.remove)
    client.message_callback_add(f'snapclient/{site_id}/startService', sc.start)
    client.message_callback_add(f'snapclient/{site_id}/stopService', sc.stop)
    client.message_callback_add('bluetooth/update/requestDeviceLists', bl.send_device_lists)
    client.subscribe(f'bluetooth/ask/{site_id}/#')
    client.subscribe(f'snapclient/{site_id}/#')
    client.subscribe('bluetooth/update/requestDeviceLists')


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

    bl = bluetoothctl.Bluetooth(mqtt_client, site_id)
    bl.send_device_lists()
    sc = snapclientctl.SnapclientControll()

    mqtt_client.loop_forever()
