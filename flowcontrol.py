import json
import re
import random


class FlowControll:
    def __init__(self, mqtt_client, config, bltctl, sncctl, mpdctl):
        self.mqtt_client = mqtt_client
        self.config = config
        self.bltctl = bltctl
        self.sncctl = sncctl
        self.mpdctl = mpdctl
        self.site_id = config['snips']['device']['site_id']
        self.room_name = config['snips']['device']['room_name']

    def send_site_info(self):
        payload = {
            'room_name': self.room_name,
            'site_id': self.site_id,
            'mpd_status': self.config['mpd']['common']['is_active'],
            'available_blt_devices': [d['name'] if d['name'] not in self.bltctl.synonyms
                                      else self.bltctl.synonyms[d['name']]
                                      for d in self.bltctl.bl_helper.get_available_devices()],
            'conf_blt_devices': [d if d not in self.config['bluetooth']['synonyms']
                                 else self.config['bluetooth']['synonyms'][d]
                                 for d in self.config['bluetooth']['soundcards']],
            'conf_nonblt_devices': [d for d in self.config['snapcast']['nbsoundcards']]
        }
        self.mqtt_client.publish('snapcast/answer/siteInfo', payload=json.dumps(payload))

    def msg_send_site_info(self, client, userdata, msg):
        self.send_site_info()

    def msg_send_mpd_database_content(self, client, userdata, msg):
        artists = list()
        for line in self.mpdctl.list_type('artist'):
            artists += re.split(r'; |;|, |,', line)
        albums = self.mpdctl.list_type('album')
        titles = self.mpdctl.list_type('title')
        payload = {'artists': artists, 'albums': albums, 'titles': titles, 'site_id': self.site_id}
        self.mqtt_client.publish('snapcast/answer/siteMusic', payload=json.dumps(payload))

    def get_device_info(self, slot_device):
        if not slot_device:
            # Take the default soundcard
            soundcard = self.config['snapcast']['common']['default_soundcard']
            if soundcard in self.config['bluetooth']['soundcards'].values():
                # It's a bluetooth soundcard
                blt_soundcards = self.config['bluetooth']['soundcards']
                real_name = [real_name for real_name in blt_soundcards if blt_soundcards[real_name] == soundcard][0]
                available_bluetooth_devices = self.bltctl.bl_helper.get_available_devices()
                addr = [d['mac_address'] for d in available_bluetooth_devices if d['name'] == real_name][0]
                info_dict = {'bluetooth': {'addr': addr}, 'soundcard': soundcard, 'real_name': real_name}
            else:
                # It's a non-bluetooth soundcard
                nonblt_soundcards = self.config['snapcast']['nbsoundcards']
                real_name = [real_name for real_name in nonblt_soundcards
                             if nonblt_soundcards[real_name] == soundcard][0]
                info_dict = {'bluetooth': None, 'soundcard': soundcard, 'real_name': real_name}
        else:
            if slot_device in self.config['snapcast']['nbsoundcards']:
                # It's not a bluetooth device
                soundcard = self.config['snapcast']['nbsoundcards'][slot_device]
                nonblt_soundcards = self.config['snapcast']['nbsoundcards']
                real_name = [real_name for real_name in nonblt_soundcards
                             if nonblt_soundcards[real_name] == soundcard][0]
                info_dict = {'bluetooth': None, 'soundcard': soundcard, 'real_name': real_name}
            elif slot_device in self.config['bluetooth']['soundcards'] or \
                    slot_device in self.config['bluetooth']['synonyms'].values():
                # It's a bluetooth device
                blt_soundcards = self.config['bluetooth']['soundcards']
                blt_synonyms = self.config['bluetooth']['synonyms']
                real_name = [real_name for real_name in blt_soundcards
                             if real_name == slot_device or blt_synonyms[real_name] == slot_device][0]
                soundcard = self.config['bluetooth']['soundcards'][real_name]
                available_bluetooth_devices = self.bltctl.bl_helper.get_available_devices()
                addr = [d['mac_address'] for d in available_bluetooth_devices if d['name'] == real_name][0]
                info_dict = {'bluetooth': {'addr': addr}, 'soundcard': soundcard, 'real_name': real_name}
            else:
                # Device doesn't exist
                info_dict = None
        return info_dict

    def msg_play_music(self, client, userdata, msg):
        data = json.loads(msg.payload.decode("utf-8"))

        if data.get('artist') or data.get('album') or data.get('title'):
            # Filter songs -> var songs is a list which contains paths of filtered songs
            songs = self.mpdctl.search_songs(data.get('artist'), data.get('album'), data.get('title'))
            if not songs:
                payload = {'err': "no such songs", 'site_id': self.site_id}
                self.mqtt_client.publish('snapcast/answer/playMusic', payload=json.dumps(payload))
                return
            if data.get('artist') and not data.get('album') and not data.get('title'):
                random.shuffle(songs)
        else:
            # Make shuffled queue
            all_titles = self.mpdctl.list_type('title')
            while len(all_titles) > int(self.config['mpd']['common']['shuffled_max_len']):
                del all_titles[random.randrange(0, len(all_titles))]
            songs = [self.mpdctl.find_type('title', title) for title in all_titles]
            random.shuffle(songs)

        device_info = self.get_device_info(data['device'])

        if not device_info:
            payload = {'err': "no such device", 'site_id': self.site_id}
            self.mqtt_client.publish('snapcast/answer/playMusic', payload=json.dumps(payload))
            return

        if device_info.get('bluetooth'):
            addr = device_info['bluetooth']['addr']
            result = self.bltctl.bl_helper.connect(addr)
            if not result:
                payload = {'err': "cannot connect to bluetooth device", 'site_id': self.site_id}
                self.mqtt_client.publish('snapcast/answer/playMusic', payload=json.dumps(payload))
                return
        # TODO: Latency
        self.sncctl.snapclientctl.service_start(device_info['soundcard'], 0, device_info['real_name'])

        self.mpdctl.play_songs(songs)
