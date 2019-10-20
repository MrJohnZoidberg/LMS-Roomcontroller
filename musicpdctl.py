import pexpect


class MPDControll:
    def __init__(self):
        pass

    @staticmethod
    def list_type(mpd_type):
        command = f'mpc list {mpd_type}'
        process = pexpect.spawnu(command, echo=False, timeout=3)
        process.expect([pexpect.EOF])
        out = process.before.split("\r\n")
        return [entry for entry in out if entry]

    @staticmethod
    def find_type(mpd_type, query):
        command = f'mpc find {mpd_type} \"{query}\"'
        process = pexpect.spawnu(command, echo=False, timeout=3)
        process.expect([pexpect.EOF])
        out = process.before.split("\r\n")
        print(len(out))
        return out[0]

    @staticmethod
    def search_songs(artist=None, album=None, title=None):
        command_parts = ['mpc search']
        if artist:
            command_parts.append(f'artist "{artist}"')
        if album:
            command_parts.append(f'album "{album}"')
        if title:
            command_parts.append(f'title "{title}"')
        command = " ".join(command_parts)
        process = pexpect.spawnu(command, echo=False, timeout=3)
        process.expect([pexpect.EOF])
        out = process.before.split("\r\n")
        return [song for song in out if song]

    def play_songs(self, songs):
        self.stop_playback()
        self.delete_queue()
        for song in songs:
            self.add_song_to_queue(song)
            if song == songs[0]:
                self.start_playback()

    def stop_playback(self):
        process = pexpect.spawnu("mpc stop", echo=False, timeout=10)
        process.expect([pexpect.EOF])

    def start_playback(self):
        process = pexpect.spawnu("mpc play", echo=False, timeout=10)
        process.expect([pexpect.EOF])

    def delete_queue(self):
        process = pexpect.spawnu("mpc clear", echo=False, timeout=2)
        process.expect([pexpect.EOF])

    def add_song_to_queue(self, song):
        process = pexpect.spawnu(f'mpc add \"{song}\"', echo=False, timeout=8)
        process.expect([pexpect.EOF])
