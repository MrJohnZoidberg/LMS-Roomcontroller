#!/usr/bin/python3

import paho.mqtt.client as mqtt
import json
import toml
import threading
import blctl
import time
import pexpect

MQTT_BROKER_ADDRESS = "localhost:1883"
MQTT_USERNAME = None
MQTT_PASSWORD = None


class SnapclientControll:
    def __init__(self):
        pass

    @staticmethod
    def get_soundcard(device_name):
        soundcard_dict = {pair.split(":")[0]: pair.split(":")[1] for pair in config['device']['soundcards'].split(",")}
        if device_name in soundcard_dict:
            return soundcard_dict[device_name]
        else:
            return None

    @staticmethod
    def is_active(soundcard):
        expect_list = ["active (running)", "inactive (dead)"]
        result = pexpect.spawnu(f"systemctl status snapclient@{soundcard}").expect(expect_list) == 0
        return result


class Bluetooth:
    def __init__(self):
        self.threadobj_discover = None
        self.threadobj_connect = None
        self.threadobj_disconnect = None
        self.threadobj_trust = None
        self.threadobj_untrust = None
        self.threadobj_remove = None
        self.threadobjs_wait_disconnect = dict()
        self.connected_addresses = list()
        self.ctl = blctl.Bluetoothctl()

    def get_name_from_addr(self, addr):
        addr_dict = {device['mac_address']: device['name'] for device in self.ctl.get_available_devices()}
        return addr_dict[addr]

    def thread_wait_until_disconnect(self, addr):
        self.ctl.wait_for_disconnect(addr)
        if addr in self.connected_addresses:
            self.connected_addresses = [addr for addr in self.connected_addresses if not addr]
            # TODO: Stop Snapclient service
            print("Stop Snapclient@{}".format(sc.get_soundcard(self.get_name_from_addr(addr))))
            print("Is active", sc.is_active(sc.get_soundcard(self.get_name_from_addr(addr))))
            self.send_device_lists()
            payload = {'siteId': site_id, 'result': True, 'addr': addr}
            mqtt_client.publish(f'bluetooth/result/deviceDisconnect', payload=json.dumps(payload))

    def thread_discover(self):
        result = self.ctl.start_discover()
        payload = {'siteId': site_id, 'result': result}
        mqtt_client.publish(f'bluetooth/result/devicesDiscover', payload=json.dumps(payload))
        if not result:
            return
        for i in range(30):
            time.sleep(1)
        self.send_device_lists()
        payload = {'discoverable_devices': self.ctl.get_discoverable_devices(),
                   'siteId': site_id}
        mqtt_client.publish(f'bluetooth/result/devicesDiscovered', payload=json.dumps(payload))

    def thread_connect(self, addr):
        result = self.ctl.connect(addr)
        if result:
            if addr not in self.connected_addresses:
                self.connected_addresses.append(addr)
            self.threadobjs_wait_disconnect[addr] = threading.Thread(target=self.thread_wait_until_disconnect,
                                                                     args=(addr,))
            self.threadobjs_wait_disconnect[addr].start()
            self.send_device_lists()
        payload = {'siteId': site_id, 'result': result, 'addr': addr}
        mqtt_client.publish(f'bluetooth/result/deviceConnect', payload=json.dumps(payload))

    def thread_disconnect(self, addr):
        result = self.ctl.disconnect(addr)
        if result:
            if addr in self.connected_addresses:
                self.connected_addresses = [addr for addr in self.connected_addresses if not addr]
            self.send_device_lists()
            if self.threadobjs_wait_disconnect[addr]:
                del self.threadobjs_wait_disconnect[addr]
        payload = {'siteId': site_id, 'result': result, 'addr': addr}
        mqtt_client.publish(f'bluetooth/result/deviceDisconnect', payload=json.dumps(payload))

    def thread_trust(self, addr):
        result = self.ctl.trust(addr)
        payload = {'siteId': site_id, 'result': result, 'addr': addr}
        mqtt_client.publish(f'bluetooth/result/deviceTrust', payload=json.dumps(payload))

    def thread_untrust(self, addr):
        result = self.ctl.untrust(addr)
        payload = {'siteId': site_id, 'result': result, 'addr': addr}
        mqtt_client.publish(f'bluetooth/result/deviceUntrust', payload=json.dumps(payload))

    def thread_remove(self, addr):
        result = self.ctl.remove(addr)
        if result:
            self.send_device_lists()
        payload = {'siteId': site_id, 'result': result, 'addr': addr}
        mqtt_client.publish(f'bluetooth/result/deviceRemove', payload=json.dumps(payload))

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

    def disconnect(self, client, userdata, msg):
        data = json.loads(msg.payload.decode("utf-8"))
        if self.threadobj_disconnect:
            del self.threadobj_disconnect
        self.threadobj_disconnect = threading.Thread(target=self.thread_disconnect, args=(data['addr'],))
        self.threadobj_disconnect.start()

    def trust(self, client, userdata, msg):
        data = json.loads(msg.payload.decode("utf-8"))
        if self.threadobj_trust:
            del self.threadobj_trust
        self.threadobj_trust = threading.Thread(target=self.thread_trust, args=(data['addr'],))
        self.threadobj_trust.start()

    def untrust(self, client, userdata, msg):
        data = json.loads(msg.payload.decode("utf-8"))
        if self.threadobj_untrust:
            del self.threadobj_untrust
        self.threadobj_untrust = threading.Thread(target=self.thread_untrust, args=(data['addr'],))
        self.threadobj_untrust.start()

    def remove(self, client, userdata, msg):
        data = json.loads(msg.payload.decode("utf-8"))
        if self.threadobj_remove:
            del self.threadobj_remove
        self.threadobj_remove = threading.Thread(target=self.thread_remove, args=(data['addr'],))
        self.threadobj_remove.start()

    def send_device_lists(self, client=None, userdata=None, msg=None):
        payload = {'available_devices': self.ctl.get_available_devices(),
                   'paired_devices': self.ctl.get_paired_devices(),
                   'siteId': site_id}
        mqtt_client.publish('bluetooth/update/deviceLists', payload=json.dumps(payload))


def on_connect(client, userdata, flags, rc):
    client.message_callback_add(f'bluetooth/ask/{site_id}/devicesDiscover', bl.discover)
    client.message_callback_add(f'bluetooth/ask/{site_id}/deviceConnect', bl.connect)
    client.message_callback_add(f'bluetooth/ask/{site_id}/deviceDisconnect', bl.disconnect)
    client.message_callback_add(f'bluetooth/ask/{site_id}/deviceTrust', bl.connect)
    client.message_callback_add(f'bluetooth/ask/{site_id}/deviceUntrust', bl.connect)
    client.message_callback_add(f'bluetooth/ask/{site_id}/deviceRemove', bl.remove)
    client.message_callback_add('bluetooth/update/requestDeviceLists', bl.send_device_lists)
    client.subscribe(f'bluetooth/ask/{site_id}/#')
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

    bl = Bluetooth()
    sc = SnapclientControll()

    mqtt_client = mqtt.Client()
    mqtt_client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    mqtt_client.on_connect = on_connect
    mqtt_client.connect(MQTT_BROKER_ADDRESS.split(":")[0], int(MQTT_BROKER_ADDRESS.split(":")[1]))
    bl.send_device_lists()
    mqtt_client.loop_forever()
