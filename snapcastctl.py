import pexpect
import json


class SnapclientControll:
    def __init__(self):
        pass

    @staticmethod
    def is_active(soundcard):
        expect_list = [r"active \(running\)", r"inactive \(dead\)", "could not be found"]
        result = pexpect.spawnu(f"systemctl status snapclient@{soundcard}").expect(expect_list) == 0
        return result

    @staticmethod
    def write_environment_file(soundcard, latency, client_id):
        with open("/etc/default/snapclient", "w") as f:
            args = []
            if soundcard:
                args.append(f"-s {soundcard}")
            if latency:
                args.append(f"--latency {latency}")
            if client_id:
                args.append(f"--hostID {client_id}")
            f.write('SNAPCLIENT_OPTS="{args}"\n'.format(args=" ".join(args)))

    def start(self, client, userdata, msg):
        data = json.loads(msg.payload.decode("utf-8"))
        soundcard = data['soundcard']
        addr = data['addr']
        self.write_environment_file(soundcard, 0, addr)
        expect_list = [pexpect.EOF, r"not loaded", pexpect.TIMEOUT]
        result = pexpect.spawnu(f"systemctl restart -f snapclient@{soundcard}").expect(expect_list, 4) == 0
        if result:
            print(f"Successfully started Snapclient with soundcard <{soundcard}>.")
        else:
            print(f"Failed to start Snapclient with soundcard <{soundcard}>.")

    @staticmethod
    def stop(client, userdata, msg):
        data = json.loads(msg.payload.decode("utf-8"))
        soundcard = data['soundcard']
        expect_list = [pexpect.EOF, r"not loaded", pexpect.TIMEOUT]
        result = pexpect.spawnu(f"systemctl stop -f snapclient@{soundcard}").expect(expect_list, 4) == 0
        if result:
            print(f"Successfully stopped Snapclient with soundcard <{soundcard}>.")
        else:
            print(f"Failed to stop Snapclient with soundcard <{soundcard}>.")


class SnapserverControll:
    def __init__(self):
        pass

    @staticmethod
    def is_active(soundcard):
        expect_list = [r"active \(running\)", r"inactive \(dead\)", "could not be found"]
        result = pexpect.spawnu(f"systemctl status snapclient@{soundcard}").expect(expect_list) == 0
        return result

    def start(self, client, userdata, msg):
        data = json.loads(msg.payload.decode("utf-8"))
        expect_list = [pexpect.EOF, r"not loaded", pexpect.TIMEOUT]
        result = pexpect.spawnu("systemctl restart -f snapserver").expect(expect_list, 4) == 0
        if result:
            print("Successfully started Snapserver.")
        else:
            print("Failed to start Snapserver.")

    @staticmethod
    def stop(client, userdata, msg):
        data = json.loads(msg.payload.decode("utf-8"))
        expect_list = [pexpect.EOF, r"not loaded", pexpect.TIMEOUT]
        result = pexpect.spawnu("systemctl stop -f snapserver").expect(expect_list, 4) == 0
        if result:
            print("Successfully stopped Snapserver.")
        else:
            print("Failed to stop Snapserver.")


class SnapcastControll:
    def __init__(self, mqtt_client, bltctl, mpdctl, config):
        self.mqtt_client = mqtt_client
        self.site_id = config['snips']['device']['site_id']
        self.room_name = config['snips']['device']['room_name']
        self.bltctl = bltctl
        self.mpdctl = mpdctl
        self.config = config

    def send_site_info(self, client=None, userdata=None, msg=None):
        payload = {'room_name': self.room_name, 'site_id': self.site_id}
        self.mqtt_client.publish('snapcast/answer/siteInfo', payload=json.dumps(payload))

    def send_device_names(self, client, userdata, msg):
        available_bluetooth_devices = [d['name'] for d in self.bltctl.bl_helper.get_available_devices()]
        configured_bluetooth_devices = [d if d not in self.config['bluetooth']['synonyms']
                                        else self.config['bluetooth']['synonyms'][d]
                                        for d in self.config['bluetooth']['soundcards']]
        configured_nonbluetooth_devices = [d for d in self.config['snapcast']['nbsoundcards']]
        all_names = available_bluetooth_devices + configured_bluetooth_devices + configured_nonbluetooth_devices
        filtered_names = list()
        for name in all_names:
            if name not in filtered_names:
                filtered_names.append(name)
        payload = {'names': filtered_names, 'site_id': self.site_id}
        self.mqtt_client.publish('snapcast/answer/siteDevices', payload=json.dumps(payload))

    def send_music_names(self, client, userdata, msg):
        artists = self.mpdctl.get_all_artists()
        albums = self.mpdctl.get_all_albums()
        titles = self.mpdctl.get_all_titles()
        print(artists, albums, titles)
        #payload = {'artists': artists, 'albums': albums, 'titles': titles, 'site_id': self.site_id}
        #self.mqtt_client.publish('snapcast/answer/siteMusic', payload=json.dumps(payload))

    def set_volume(self, slot_dict):
        url = f"http:///jsonrpc"
        headers = {'content-type': 'application/json'}
        # Example echo method
        payload = {"id": 8, "jsonrpc": "2.0", "method": "Client.GetStatus", "params": {"id": "b8:27:eb:65:d2:48"}}
        #response = requests.post(url, data=json.dumps(payload), headers=headers).json()
        #print(response)
