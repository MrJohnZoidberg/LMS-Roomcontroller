#!/usr/bin/python3

import toml
import paho.mqtt.client as mqtt
import bluetoothctl
import squeezelitectl
import flowcontrol

MQTT_BROKER_ADDRESS = "localhost:1883"
MQTT_USERNAME = None
MQTT_PASSWORD = None


def on_connect(client, userdata, flags, rc):
    client.message_callback_add(f'bluetooth/request/oneSite/{site_id}/devicesDiscover', bltctl.msg_discover)
    client.message_callback_add(f'bluetooth/request/oneSite/{site_id}/deviceConnect', bltctl.msg_connect)
    client.message_callback_add(f'bluetooth/request/oneSite/{site_id}/deviceDisconnect', bltctl.msg_disconnect)
    client.message_callback_add(f'bluetooth/request/oneSite/{site_id}/deviceRemove', bltctl.msg_remove)
    client.message_callback_add(f'bluetooth/request/oneSite/{site_id}/siteInfo', bltctl.msg_send_blt_info)
    client.message_callback_add('bluetooth/request/allSites/siteInfo', bltctl.msg_send_blt_info)
    client.subscribe(f'bluetooth/request/oneSite/{site_id}/#')
    client.subscribe('bluetooth/request/allSites/#')

    client.message_callback_add(f'squeezebox/request/oneSite/{site_id}/serviceStart', flowctl.msg_service_start)
    client.message_callback_add(f'squeezebox/request/oneSite/{site_id}/serviceStop', flowctl.msg_service_stop)
    client.message_callback_add(f'squeezebox/request/oneSite/{site_id}/siteInfo', flowctl.msg_send_site_info)
    client.subscribe(f'squeezebox/request/oneSite/{site_id}/#')

    client.message_callback_add('squeezebox/request/allSites/siteInfo', flowctl.msg_send_site_info)
    client.subscribe('squeezebox/request/allSites/#')


if __name__ == "__main__":
    config = toml.load('config.toml')
    if 'mqtt' in config['snips']['common']:
        MQTT_BROKER_ADDRESS = config['snips']['common']['mqtt']
    if 'mqtt_username' in config['snips']['common']:
        MQTT_USERNAME = config['snips']['common']['mqtt_username']
    if 'mqtt_password' in config['snips']['common']:
        MQTT_PASSWORD = config['snips']['common']['mqtt_password']
    site_id = config['snips']['site']['site_id']

    mqtt_client = mqtt.Client()

    bltctl = bluetoothctl.Bluetooth(mqtt_client, config)
    sqectl = squeezelitectl.SqueezeliteControll()
    flowctl = flowcontrol.FlowControll(mqtt_client, config, bltctl, sqectl)

    mqtt_client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    mqtt_client.on_connect = on_connect
    mqtt_client.connect(MQTT_BROKER_ADDRESS.split(":")[0], int(MQTT_BROKER_ADDRESS.split(":")[1]))

    bltctl.send_blt_info()
    flowctl.send_site_info()
    mqtt_client.loop_forever()
