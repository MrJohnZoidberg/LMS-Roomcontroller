import pexpect


class SqueezeliteControll:
    def __init__(self):
        pass

    @staticmethod
    def is_active():
        expect_list = [r"active \(running\)", r"inactive \(dead\)", "could not be found"]
        result = pexpect.spawnu(f"systemctl status squeezelite").expect(expect_list) == 0
        return result

    @staticmethod
    def write_environment_file(soundcard):
        with open("/etc/default/snapclient", "w") as f:
            args = []
            if soundcard:
                args.append(f"-s {soundcard}")
            if latency:
                args.append(f"--latency {latency}")
            if client_id:
                args.append(f"--hostID {client_id}")
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


class SnapserverControll:
    def __init__(self):
        pass

    @staticmethod
    def is_active():
        expect_list = [r"active \(running\)", r"inactive \(dead\)", "could not be found"]
        result = pexpect.spawnu("systemctl status snapserver").expect(expect_list) == 0
        return result

    @staticmethod
    def start(client, userdata, msg):
        expect_list = [pexpect.EOF, r"not loaded", pexpect.TIMEOUT]
        result = pexpect.spawnu("systemctl restart -f snapserver").expect(expect_list, 4) == 0
        if result:
            print("Successfully started Snapserver.")
        else:
            print("Failed to start Snapserver.")

    @staticmethod
    def stop(client, userdata, msg):
        expect_list = [pexpect.EOF, r"not loaded", pexpect.TIMEOUT]
        result = pexpect.spawnu("systemctl stop -f snapserver").expect(expect_list, 4) == 0
        if result:
            print("Successfully stopped Snapserver.")
        else:
            print("Failed to stop Snapserver.")
