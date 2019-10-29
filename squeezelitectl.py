import pexpect


class SqueezeliteControll:
    def __init__(self, config):
        self.config = config
        pass

    @staticmethod
    def is_active(squeeze_mac):
        expect_list = [r"active \(running\)", r"inactive \(dead\)", "could not be found", "failed"]
        result = pexpect.spawnu(f"systemctl status squeezelite@{squeeze_mac}").expect(expect_list) == 0
        return result

    @staticmethod
    def write_environment_file(server, squeeze_mac, soundcard, name):
        with open("/etc/default/squeezelite", "w") as f:
            args = [f"-s {server} -m {squeeze_mac}", f"-o {soundcard}", f"-n {name.replace(' ', '')}"]
            f.write('SB_EXTRA_ARGS=\"{args}\"\n'.format(args=" ".join(args)))

    def service_start(self, server, squeeze_mac, soundcard, name):
        self.write_environment_file(server, squeeze_mac, soundcard, name)
        expect_list = [pexpect.EOF, pexpect.TIMEOUT]
        result = pexpect.spawnu(f"systemctl start -f squeezelite").expect(expect_list, 4) == 0
        if result:
            print(f"Successfully started Squeezelite.")
        else:
            print(f"Failed to start Squeezelite.")
        return result

    @staticmethod
    def service_stop():
        expect_list = [pexpect.EOF, pexpect.TIMEOUT]
        result = pexpect.spawnu(f"systemctl stop -f squeezelite").expect(expect_list, 4) == 0
        if not result:
            result = pexpect.spawnu(f"systemctl kill squeezelite").expect(expect_list, 4) == 0
        if result:
            print(f"Successfully stopped Squeezelite.")
        else:
            print(f"Failed to stop Squeezelite.")
        return result
