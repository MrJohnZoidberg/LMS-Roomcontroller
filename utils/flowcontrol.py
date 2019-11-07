import json
import pickle
import random
import threading
import time
from . import bluetoothctl, squeezelitectl


class FlowControll:
    def __init__(self, mqtt_client, config):
        self.mqtt_client = mqtt_client
        self.config = config
        self.bltctl = bluetoothctl.Bluetooth(self.mqtt_client, self.config)
        self.sqectl = squeezelitectl.SqueezeliteControll()
        self.msg_send_site_info(self.mqtt_client)

    @staticmethod
    def create_mac():
        mac = "%02x:%02x:%02x:%02x:%02x:%02x" % (
            random.randint(0, 255),
            random.randint(0, 255),
            random.randint(0, 255),
            random.randint(0, 255),
            random.randint(0, 255),
            random.randint(0, 255)
        )
        return mac

    def get_squeezelite_mac(self, device_name, devices_macs):
        try:
            with open(".squeezelite_macs", "rb") as f:
                macs_file_dict = pickle.load(f)
        except FileNotFoundError:
            macs_file_dict = dict()
        if not devices_macs.get(device_name):
            macs_file_dict[device_name] = self.create_mac()
        else:
            macs_file_dict[device_name] = devices_macs.get(device_name)
        with open(".squeezelite_macs", "wb") as f:
            pickle.dump(macs_file_dict, f)
        return macs_file_dict.get(device_name)

    def get_device_list(self):
        devices = list()
        devices_names = self.config['devices']['names']
        devices_soundcards = self.config['devices']['soundcards']
        devices_macs = self.config['devices']['macs']
        available_bluetooth_devices = self.bltctl.bl_helper.get_available_devices()

        for name in devices_names:
            names_list = [name]  # list with all names from site

            synonyms = devices_names[name]
            if synonyms and isinstance(synonyms, str):
                names_list.append(synonyms)
                synonyms = [synonyms]
            elif synonyms and isinstance(synonyms, list):
                for synonym in synonyms:
                    names_list.append(synonym)
            else:
                synonyms = None

            addr = [d['mac_address'] for d in available_bluetooth_devices if d['name'] == name]
            if addr:
                bluetooth_info = {'addr': addr[0],
                                  'is_connected': self.bltctl.bl_helper.is_connected(addr[0])}
            else:
                bluetooth_info = dict()

            device = {
                'name': name,
                'names_list': names_list,
                'synonyms': synonyms,
                'bluetooth': bluetooth_info,
                'soundcard': devices_soundcards.get(name),
                'squeezelite_mac': self.get_squeezelite_mac(name, devices_macs)
            }
            devices.append(device)
        return devices

    def msg_send_site_info(self, *args):
        client = args[0]
        payload = {
            'room_name': self.config['snips']['site']['room_name'],
            'site_id': self.config['snips']['site']['site_id'],
            'area': self.config['snips']['site']['area'],
            'devices': self.get_device_list(),
            'default_device': self.config['squeezelite']['default_device'],
            'auto_pause': self.config['squeezelite']['pause_while_dialogue']
        }
        client.publish('squeezebox/answer/siteInfo', payload=json.dumps(payload))

    @staticmethod
    def thread_wait_few_seconds(client, payload):
        time.sleep(4)
        client.publish('squeezebox/answer/serviceStart', payload=json.dumps(payload))

    def msg_service_start(self, *args):
        data = json.loads(args[2].payload.decode("utf-8"))
        timeout = self.config['devices']['timeouts'].get(data['device_name'])
        if timeout:
            timeout = int(timeout)
        result = self.sqectl.service_start(
            data['server'],
            data['squeeze_mac'],
            data['soundcard'],
            data['player_name'],
            timeout,
        )
        payload = {
            'siteId': self.config['snips']['site']['site_id'],
            'result': result
        }
        self.msg_send_site_info(args[0])
        threading.Thread(target=self.thread_wait_few_seconds, args=(args[0], payload,)).start()

    def msg_service_stop(self, *args):
        client = args[0]
        result = self.sqectl.service_stop()
        payload = {
            'siteId': self.config['snips']['site']['site_id'],
            'result': result
        }
        self.msg_send_site_info(client)
        client.publish('squeezebox/answer/serviceStop', payload=json.dumps(payload))
