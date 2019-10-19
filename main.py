#!/usr/bin/python3

import toml
import paho.mqtt.client as mqtt
import bluetoothctl
import snapcastctl
import musicpdctl

MQTT_BROKER_ADDRESS = "localhost:1883"
MQTT_USERNAME = None
MQTT_PASSWORD = None


def on_connect(client, userdata, flags, rc):
    client.message_callback_add(f'bluetooth/request/oneSite/{site_id}/devicesDiscover', bltctl.discover)
    client.message_callback_add(f'bluetooth/request/oneSite/{site_id}/deviceConnect', bltctl.connect)
    client.message_callback_add(f'bluetooth/request/oneSite/{site_id}/deviceDisconnect', bltctl.disconnect)
    client.message_callback_add(f'bluetooth/request/oneSite/{site_id}/deviceRemove', bltctl.remove)
    client.message_callback_add(f'bluetooth/request/oneSite/{site_id}/deviceLists', bltctl.send_device_lists)
    client.message_callback_add(f'bluetooth/request/oneSite/{site_id}/siteInfo', bltctl.send_site_info)
    client.message_callback_add('bluetooth/request/allSites/deviceLists', bltctl.send_device_lists)
    client.message_callback_add('bluetooth/request/allSites/siteInfo', bltctl.send_site_info)
    client.subscribe(f'bluetooth/request/oneSite/{site_id}/#')
    client.subscribe('bluetooth/request/allSites/#')

    client.message_callback_add('snapcast/request/allSites/siteDevices', sncctl.send_device_names)
    client.subscribe('snapcast/request/allSites/#')


if __name__ == "__main__":
    config = toml.load('config.toml')
    if 'mqtt' in config['snips']['common']:
        MQTT_BROKER_ADDRESS = config['snips']['common']['mqtt']
    if 'mqtt_username' in config['snips']['common']:
        MQTT_USERNAME = config['snips']['common']['mqtt_username']
    if 'mqtt_password' in config['snips']['common']:
        MQTT_PASSWORD = config['snips']['common']['mqtt_password']
    site_id = config['snips']['device']['site_id']
    room_name = config['snips']['device']['room_name']

    mqtt_client = mqtt.Client()

    bltctl = bluetoothctl.Bluetooth(mqtt_client, config)
    mpdctl = musicpdctl.MPDControll(config['mpd'])
    sncctl = snapcastctl.SnapcastControll(mqtt_client, bltctl, mpdctl, config)

    mqtt_client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    mqtt_client.on_connect = on_connect
    mqtt_client.connect(MQTT_BROKER_ADDRESS.split(":")[0], int(MQTT_BROKER_ADDRESS.split(":")[1]))

    bltctl.send_site_info()
    bltctl.send_device_lists()
    sncctl.send_site_info()
    mqtt_client.loop_forever()
