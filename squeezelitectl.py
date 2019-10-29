import pexpect


class SqueezeliteControll:
    @staticmethod
    def is_active(squeeze_mac):
        expect_list = [r"active \(running\)", r"inactive \(dead\)", "could not be found", "failed"]
        result = pexpect.spawnu(f"systemctl status squeezelite@{squeeze_mac}").expect(expect_list) == 0
        return result

    @staticmethod
    def write_environment_file(server, squeeze_mac, soundcard, name, timeout):
        with open("/etc/default/squeezelite", "w") as f:
            args = [
                f"-s {server} -m {squeeze_mac}",
                f"-o {soundcard}",
                f"-C {timeout}",
                f"-n {name.replace(' ', '')}",
            ]
            f.write('SB_EXTRA_ARGS=\"{args}\"\n'.format(args=" ".join(args)))

    def service_start(self, server, squeeze_mac, soundcard, name, timeout):
        self.write_environment_file(server, squeeze_mac, soundcard, name, timeout)
        expect_list = [r"Failed to start squeezelite.service", pexpect.EOF, pexpect.TIMEOUT]
        result = pexpect.spawnu(f"systemctl start -f squeezelite").expect(expect_list, 4) == 1
        if result:
            print(f"Successfully started Squeezelite.")
        else:
            print(f"Failed to start Squeezelite.")
        return result

    @staticmethod
    def service_stop():
        expect_list = [r"Failed to stop squeezelite.service", pexpect.EOF, pexpect.TIMEOUT]
        result = pexpect.spawnu(f"systemctl stop -f squeezelite").expect(expect_list, 4) == 1
        if not result:
            expect_list = [r"Failed to kill unit squeezelite.service", pexpect.EOF, pexpect.TIMEOUT]
            result = pexpect.spawnu(f"systemctl kill squeezelite").expect(expect_list, 4) == 0
        if result:
            print(f"Successfully stopped Squeezelite.")
        else:
            print(f"Failed to stop Squeezelite.")
        return result
