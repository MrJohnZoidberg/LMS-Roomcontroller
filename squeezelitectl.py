import pexpect


class SqueezeliteControll:
    def __init__(self, config):
        self.config = config
        pass

    @staticmethod
    def is_active():
        expect_list = [r"active \(running\)", r"inactive \(dead\)", "could not be found"]
        result = pexpect.spawnu(f"systemctl status squeezelite").expect(expect_list) == 0
        return result

    def write_environment_file(self, soundcard):
        with open("/etc/default/squeezelite", "w") as f:
            args = []
            if soundcard:
                args.append(f"-o {soundcard}")
            name = self.config['snips']['device']['room_name']
            args.append(f"-n \'{name}\'")
            f.write('SNAPCLIENT_OPTS="{args}"\n'.format(args=" ".join(args)))

    def service_start(self, soundcard):
        self.write_environment_file(soundcard)
        expect_list = [pexpect.EOF, r"not loaded", pexpect.TIMEOUT]
        result = pexpect.spawnu(f"systemctl restart -f squeezelite").expect(expect_list, 4) == 0
        if result:
            print(f"Successfully started Squeezelite.")
        else:
            print(f"Failed to start Squeezelite.")
        return result

    def service_stop(self):
        expect_list = [pexpect.EOF, r"not loaded", pexpect.TIMEOUT]
        result = pexpect.spawnu(f"systemctl stop -f squeezelite").expect(expect_list, 4) == 0
        if result:
            print(f"Successfully stopped Squeezelite.")
        else:
            print(f"Failed to stop Squeezelite.")
        return result
