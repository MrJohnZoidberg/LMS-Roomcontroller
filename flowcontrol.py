import json
import pickle
import random


class FlowControll:
    def __init__(self, mqtt_client, config, bltctl, sqectl):
        self.mqtt_client = mqtt_client
        self.config = config
        self.bltctl = bltctl
        self.sqectl = sqectl
        self.site_id = config['snips']['device']['site_id']
        self.room_name = config['snips']['device']['room_name']
        self.area = config['snips']['device']['area']
        self.device_list = list()

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

    def get_squeezelite_mac(self, device_name):
        try:
            with open(".squeezelite_macs", "rb") as f:
                macs_dict = pickle.load(f)
        except FileNotFoundError:
            macs_dict = dict()
        if not macs_dict.get(device_name):
            macs_dict[device_name] = self.create_mac()
            with open(".squeezelite_macs", "wb") as f:
                pickle.dump(macs_dict, f)
        return macs_dict.get(device_name)

    def get_device_list(self):
        devices = list()
        blt_soundcards = self.config['bluetooth']['soundcards']
        blt_synonyms = self.config['bluetooth']['synonyms']
        # nonblt_soundcards = self.config['squeezelite']['nbsoundcards']
        available_bluetooth_devices = self.bltctl.bl_helper.get_available_devices()

        for name in blt_soundcards:
            names_list = [name]
            if name in blt_synonyms:
                synonym = blt_synonyms[name]
                names_list.append(synonym)
            else:
                synonym = None
            addr = [d['mac_address'] for d in available_bluetooth_devices if d['name'] == name]
            if addr:
                addr = addr[0]
            else:
                addr = None
            device = {
                'name': name,
                'names_list': names_list,
                'synonym': synonym,
                'bluetooth': {'addr': addr,
                              'is_connected': self.bltctl.bl_helper.is_connected(addr)},
                'soundcard': blt_soundcards[name],
                'squeezelite_mac': self.get_squeezelite_mac(name)
            }
            devices.append(device)

        """
        for name in nonblt_soundcards:
            device = {
                'name': name,
                'names_list': [name],
                'synonym': None,
                'bluetooth': None,
                'soundcard': nonblt_soundcards[name]
            }
            devices.append(device)
        """
        self.device_list = devices
        return devices

    def send_site_info(self):
        payload = {
            'room_name': self.room_name,
            'site_id': self.site_id,
            'area': self.area,
            'devices': self.get_device_list(),
            'default_device': self.config['squeezelite']['default_device'],
            'auto_pause': self.config['squeezelite']['pause_while_dialogue']
        }
        self.mqtt_client.publish('squeezebox/answer/siteInfo', payload=json.dumps(payload))

    def msg_send_site_info(self, client, userdata, msg):
        self.send_site_info()

    def msg_service_start(self, client, userdata, msg):
        data = json.loads(msg.payload.decode("utf-8"))
        mac = data['squeeze_mac']
        if self.sqectl.is_active(mac):
            result = True
        else:
            result = self.sqectl.service_start(mac, data['soundcard'], data['name'])
        payload = {
            'siteId': self.site_id,
            'result': result
        }
        self.send_site_info()
        client.publish('squeezebox/answer/serviceStart', payload=json.dumps(payload))

    def msg_service_stop(self, client, userdata, msg):
        result = self.sqectl.service_stop()
        payload = {
            'siteId': self.site_id,
            'result': result
        }
        self.send_site_info()
        client.publish('squeezebox/answer/serviceStop', payload=json.dumps(payload))
