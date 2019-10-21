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
            'mpd_status': self.config['mpd']['common']['is_active'],
            'devices': self.get_device_list()
        }
        self.mqtt_client.publish('snapcast/answer/siteInfo', payload=json.dumps(payload))

    def msg_send_site_info(self, client, userdata, msg):
        self.send_site_info()

    def msg_send_mpd_database_content(self, client, userdata, msg):
        artists = list()
        for line in self.mpdctl.list_type('artist'):
            for artist in re.split(r'; |;|, |,', line):
                if artist:
                    artists.append(artist)
        albums = self.mpdctl.list_type('album')
        titles = self.mpdctl.list_type('title')
        genres = list()
        for line in self.mpdctl.list_type('genre'):
            for genre in re.split(r'; |;|, |,|/| / ', line):
                if genre:
                    genres.append(genre)
        payload = {
            'artists': artists,
            'albums': albums,
            'titles': titles,
            'genres': genres,
            'site_id': self.site_id
        }
        self.mqtt_client.publish('snapcast/answer/siteMusic', payload=json.dumps(payload))

    def msg_disconnected(self, client, userdata, msg):
        data = json.loads(msg.payload.decode("utf-8"))
        if data['siteId'] == self.site_id:
            soundcard = [d['soundcard'] for d in self.get_device_list()
                         if d.get('bluetooth') and d['bluetooth']['addr'] == data['addr']]
            if soundcard:
                self.sncctl.snapclientctl.service_stop(soundcard[0])

    def msg_play_music(self, client, userdata, msg):
        data = json.loads(msg.payload.decode("utf-8"))

        if not data.get('device'):
            default_soundcard = self.config['snapcast']['common']['default_soundcard']
            device_info = [d for d in self.get_device_list() if default_soundcard == d['soundcard']]
        else:
            device_info = [d for d in self.get_device_list() if data['device'] in d['names_list']]

        if not device_info:
            payload = {'err': "no such device", 'site_id': self.site_id}
            self.mqtt_client.publish('snapcast/answer/playMusic', payload=json.dumps(payload))
            return
        else:
            device_info = device_info[0]

        if device_info['bluetooth']:
            addr = device_info['bluetooth']['addr']
            if addr not in self.bltctl.connected_devices:
                result = self.bltctl.connect(addr)
                if not result:
                    payload = {'err': "cannot connect to bluetooth device", 'site_id': self.site_id}
                    self.mqtt_client.publish('snapcast/answer/playMusic', payload=json.dumps(payload))
                    return

        # TODO: Latency
        if not self.sncctl.snapclientctl.is_active(device_info['soundcard']):
            self.sncctl.snapclientctl.service_start(device_info['soundcard'], 0, device_info['name'])

        if data.get('artist') or data.get('album') or data.get('title'):
            # Filter songs -> var songs is a list which contains paths of filtered songs
            songs = self.mpdctl.search_songs(data.get('artist'), data.get('album'), data.get('title'))
            if not songs:
                payload = {'err': "no such songs", 'site_id': self.site_id}
                self.mqtt_client.publish('snapcast/answer/playMusic', payload=json.dumps(payload))
                return
            if data.get('artist') and not data.get('album') and not data.get('title'):
                random.shuffle(songs)

            self.mpdctl.stop_playback()
            self.mpdctl.delete_queue()
            for song in songs:
                self.mpdctl.add_song_to_queue(song)
                if song == songs[0]:
                    self.mpdctl.start_playback()
        else:
            # Make shuffled queue
            all_titles = self.mpdctl.list_type('title')
            while len(all_titles) > int(self.config['mpd']['common']['shuffled_max_len']):
                del all_titles[random.randrange(0, len(all_titles))]
            random.shuffle(all_titles)

            self.mpdctl.stop_playback()
            self.mpdctl.delete_queue()
            songs_added = 0
            for title in all_titles:
                song = self.mpdctl.find_type('title', title)
                if song:
                    self.mpdctl.add_song_to_queue(song)
                    songs_added += 1
                if songs_added == 1:
                    self.mpdctl.start_playback()
