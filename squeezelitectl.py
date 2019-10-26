import pexpect


class SqueezeliteControll:
    def __init__(self, config):
        self.config = config
        pass

    @staticmethod
    def is_active(squeeze_mac):
        expect_list = [r"active \(running\)", r"inactive \(dead\)", "could not be found"]
        result = pexpect.spawnu(f"systemctl status squeezelite@{squeeze_mac}").expect(expect_list) == 0
        return result

    def write_environment_file(self, squeeze_mac, soundcard, device_name):
        with open("/etc/default/squeezelite", "w") as f:
            name = self.config['snips']['device']['room_name'] + " - " + device_name
            args = [f"-m {squeeze_mac}", f"-o {soundcard}", f"-n \'{name}\'"]
            f.write('SB_EXTRA_ARGS==\"{args}\"\n'.format(args=" ".join(args)))

    def service_start(self, squeeze_mac, soundcard, name):
        self.write_environment_file(squeeze_mac, soundcard, name)
        expect_list = [pexpect.EOF, r"not loaded", pexpect.TIMEOUT]
        result = pexpect.spawnu(f"systemctl restart -f squeezelite@{squeeze_mac}").expect(expect_list, 4) == 0
        if result:
            print(f"Successfully started Squeezelite.")
        else:
            print(f"Failed to start Squeezelite.")
        return result

    def service_stop(self, squeeze_mac):
        expect_list = [pexpect.EOF, r"not loaded", pexpect.TIMEOUT]
        result = pexpect.spawnu(f"systemctl stop -f squeezelite@{squeeze_mac}").expect(expect_list, 4) == 0
        if result:
            print(f"Successfully stopped Squeezelite.")
        else:
            print(f"Failed to stop Squeezelite.")
        return result
