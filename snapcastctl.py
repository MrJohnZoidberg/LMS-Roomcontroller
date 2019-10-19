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

    def service_start(self, soundcard, latency, client_id):
        self.write_environment_file(soundcard, latency, client_id)
        expect_list = [pexpect.EOF, r"not loaded", pexpect.TIMEOUT]
        result = pexpect.spawnu(f"systemctl restart -f snapclient@{soundcard}").expect(expect_list, 4) == 0
        if result:
            print(f"Successfully started Snapclient with soundcard <{soundcard}>.")
        else:
            print(f"Failed to start Snapclient with soundcard <{soundcard}>.")
        return result

    def service_stop(self, soundcard):
        expect_list = [pexpect.EOF, r"not loaded", pexpect.TIMEOUT]
        result = pexpect.spawnu(f"systemctl stop -f snapclient@{soundcard}").expect(expect_list, 4) == 0
        if result:
            print(f"Successfully stopped Snapclient with soundcard <{soundcard}>.")
        else:
            print(f"Failed to stop Snapclient with soundcard <{soundcard}>.")
        return result

    def mqtt_start(self, client, userdata, msg):
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
    def mqtt_stop(client, userdata, msg):
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
        self.snapclientctl = SnapclientControll()
        self.config = config

    def send_site_info(self, client=None, userdata=None, msg=None):
        payload = {
            'room_name': self.room_name,
            'site_id': self.site_id,
            'mpd_status': self.config['mpd']['common']['is_active'],
            'available_blt_devices': [d['name'] if d not in self.bltctl.synonyms else self.bltctl.synonyms[d['name']]
                                      for d in self.bltctl.get_available_devices()],
            'conf_blt_devices': [d if d not in self.config['bluetooth']['synonyms']
                                 else self.config['bluetooth']['synonyms'][d]
                                 for d in self.config['bluetooth']['soundcards']],
            'conf_nonblt_devices': [d for d in self.config['snapcast']['nbsoundcards']]
        }
        self.mqtt_client.publish('snapcast/answer/siteInfo', payload=json.dumps(payload))

    def send_music_names(self, client, userdata, msg):
        artists = self.mpdctl.get_all_artists()
        albums = self.mpdctl.get_all_albums()
        titles = self.mpdctl.get_all_titles()
        payload = {'artists': artists, 'albums': albums, 'titles': titles, 'site_id': self.site_id}
        self.mqtt_client.publish('snapcast/answer/siteMusic', payload=json.dumps(payload))

    def play_music(self, client, userdata, msg):
        data = json.loads(msg.payload.decode("utf-8"))
        err, songs = self.mpdctl.get_songs(data.get('artist'), data.get('album'), data.get('title'))
        if err:
            payload = {'err': err, 'site_id': self.site_id}
            self.mqtt_client.publish('snapcast/answer/playMusic', payload=json.dumps(payload))
            return
        if data.get('device'):
            available_bluetooth_devices = self.bltctl.get_available_devices()
            names_available_devices = [d['name'] if d not in self.bltctl.synonyms else self.bltctl.synonyms[d['name']]
                                       for d in available_bluetooth_devices]
            if data['device'] in names_available_devices:
                addr = [d['mac_address'] for d in available_bluetooth_devices if d['name'] == data['device'] or
                        self.bltctl.synonyms[d['name']] == data['device']][0]
                real_name = [d['name'] for d in available_bluetooth_devices if d['name'] == data['device'] or
                             self.bltctl.synonyms[d['name']] == data['device']][0]
                result = self.bltctl.bl_helper.connect(addr)
                if not result:
                    payload = {'err': "cannot connect to bluetooth device", 'site_id': self.site_id}
                    self.mqtt_client.publish('snapcast/answer/playMusic', payload=json.dumps(payload))
                    return
                soundcard = self.config['bluetooth']['soundcards'][real_name]
                self.snapclientctl.service_start(soundcard, 0, addr)
            elif data['device'] in [d for d in self.config['snapcast']['nbsoundcards']]:
                self.snapclientctl.service_start(self.config['snapcast']['nbsoundcards'][data['device']], 0,
                                                 data['device'])

        self.mpdctl.play(songs)

    def set_volume(self, slot_dict):
        url = f"http:///jsonrpc"
        headers = {'content-type': 'application/json'}
        # Example echo method
        payload = {"id": 8, "jsonrpc": "2.0", "method": "Client.GetStatus", "params": {"id": "b8:27:eb:65:d2:48"}}
        #response = requests.post(url, data=json.dumps(payload), headers=headers).json()
        #print(response)
