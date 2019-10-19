import pexpect


class MPDControll:
    def __init__(self, config):
        self.config = config

    @staticmethod
    def list_database(mpd_type):
        process = pexpect.spawnu(f"mpc list {mpd_type}", echo=False, timeout=3)
        process.expect([pexpect.EOF])
        out = process.before
        print(out)
