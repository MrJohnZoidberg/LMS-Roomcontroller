#!/usr/bin/python3

import toml
import paho.mqtt.client as mqtt
from utils import flowcontrol
import logging

MQTT_BROKER_ADDRESS = "localhost:1883"
MQTT_USERNAME = None
MQTT_PASSWORD = None


def on_connect(*args):
    client = args[0]
    client.message_callback_add(f'bluetooth/request/oneSite/{site_id}/devicesDiscover', flowctl.bltctl.msg_discover)
    client.message_callback_add(f'bluetooth/request/oneSite/{site_id}/deviceConnect', flowctl.bltctl.msg_connect)
    client.message_callback_add(f'bluetooth/request/oneSite/{site_id}/deviceDisconnect', flowctl.bltctl.msg_disconnect)
    client.message_callback_add(f'bluetooth/request/oneSite/{site_id}/deviceRemove', flowctl.bltctl.msg_remove)
    client.message_callback_add(f'bluetooth/request/oneSite/{site_id}/siteInfo', flowctl.bltctl.msg_send_blt_info)
    client.message_callback_add('bluetooth/request/allSites/siteInfo', flowctl.bltctl.msg_send_blt_info)
    client.subscribe(f'bluetooth/request/oneSite/{site_id}/#')
    client.subscribe('bluetooth/request/allSites/#')

    client.message_callback_add(f'squeezebox/request/oneSite/{site_id}/serviceStart', flowctl.msg_service_start)
    client.message_callback_add(f'squeezebox/request/oneSite/{site_id}/serviceStop', flowctl.msg_service_stop)
    client.message_callback_add(f'squeezebox/request/oneSite/{site_id}/siteInfo', flowctl.msg_send_site_info)
    client.subscribe(f'squeezebox/request/oneSite/{site_id}/#')

    client.message_callback_add('squeezebox/request/allSites/siteInfo', flowctl.msg_send_site_info)
    client.subscribe('squeezebox/request/allSites/#')


if __name__ == "__main__":
    logging.basicConfig(filename='.controller.log', filemode='w', level=logging.DEBUG,
                        format='%(asctime)s %(levelname)s: %(message)s', datefmt='%m/%d/%Y %H:%M:%S')

    config = toml.load('config.toml')
    if 'mqtt' in config['snips']['common']:
        MQTT_BROKER_ADDRESS = config['snips']['common']['mqtt']
    if 'mqtt_username' in config['snips']['common']:
        MQTT_USERNAME = config['snips']['common']['mqtt_username']
    if 'mqtt_password' in config['snips']['common']:
        MQTT_PASSWORD = config['snips']['common']['mqtt_password']
    site_id = config['snips']['site']['site_id']

    mqtt_client = mqtt.Client()

    mqtt_client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    mqtt_client.on_connect = on_connect
    mqtt_client.connect(MQTT_BROKER_ADDRESS.split(":")[0], int(MQTT_BROKER_ADDRESS.split(":")[1]))
    logging.info(f"Connected to MQTT broker with address {MQTT_BROKER_ADDRESS}")

    flowctl = flowcontrol.FlowControll(mqtt_client, config)

    mqtt_client.loop_forever()
