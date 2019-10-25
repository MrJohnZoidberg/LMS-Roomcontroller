import json


class FlowControll:
    def __init__(self, mqtt_client, config, bltctl, sqectl):
        self.mqtt_client = mqtt_client
        self.config = config
        self.bltctl = bltctl
        self.sqectl = sqectl
        self.site_id = config['snips']['device']['site_id']
        self.room_name = config['snips']['device']['room_name']
        self.area = config['snips']['device']['area']

    def get_device_list(self):
        devices = list()
        blt_soundcards = self.config['bluetooth']['soundcards']
        blt_synonyms = self.config['bluetooth']['synonyms']
        nonblt_soundcards = self.config['snapcast']['nbsoundcards']
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
                'bluetooth': {'addr': addr},
                'soundcard': blt_soundcards[name]
            }
            devices.append(device)

        for name in nonblt_soundcards:
            device = {
                'name': name,
                'names_list': [name],
                'synonym': None,
                'bluetooth': None,
                'soundcard': nonblt_soundcards[name]
            }
            devices.append(device)
        return devices

    def send_site_info(self):
        payload = {
            'room_name': self.room_name,
            'site_id': self.site_id,
            'area': self.area,
            'devices': self.get_device_list()
        }
        self.mqtt_client.publish('snapcast/answer/siteInfo', payload=json.dumps(payload))

    def msg_send_site_info(self, client, userdata, msg):
        self.send_site_info()

    def msg_disconnected(self, client, userdata, msg):
        data = json.loads(msg.payload.decode("utf-8"))
        if data['siteId'] == self.site_id:
            soundcard = [d['soundcard'] for d in self.get_device_list()
                         if d.get('bluetooth') and d['bluetooth']['addr'] == data['addr']]
            if soundcard and self.sqectl.is_active():
                self.sqectl.service_stop()
