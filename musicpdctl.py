import pexpect
import re


class MPDControll:
    def __init__(self, config):
        self.config = config

    @staticmethod
    def list_database(mpd_type):
        process = pexpect.spawnu(f"mpc list {mpd_type}", echo=False, timeout=3)
        process.expect([pexpect.EOF])
        out = process.before.split("\n")
        return out

    def get_all_artists(self):
        output_list = self.list_database('artist')
        all_artists = list()
        for line in output_list:
            artists_line = re.split(r'; |;|, |,', line)
            for artist in artists_line:
                if artist not in all_artists and artist != "":
                    all_artists.append(artist)

    def get_all_albums(self):
        output_list = self.list_database('album')
        all_albums = list()
        for album in output_list:
            if album not in all_albums and album != "":
                all_albums.append(album)
        return all_albums

    def get_all_titles(self):
        output_list = self.list_database('title')
        all_titles = list()
        for title in output_list:
            if title not in all_titles and title != "":
                all_titles.append(title)
        return all_titles
