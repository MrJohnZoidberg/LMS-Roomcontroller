import pexpect


class SqueezeliteControll:
    @staticmethod
    def is_active():
        expect_list = [r"active \(running\)", r"inactive \(dead\)", "could not be found", "failed"]
        result = pexpect.spawnu(f"systemctl status squeezelite-custom").expect(expect_list) == 0
        return result

    @staticmethod
    def write_environment_file(server, squeeze_mac, soundcard, name, timeout):
        # TODO: Do not use the default environment file, create a new file here instead
        with open("/etc/default/squeezelite", "w") as f:
            args = [
                f"-s {server} -m {squeeze_mac}",
                f"-o {soundcard}",
                f"-C {timeout}",
                f"-n \'{name}\'",
            ]
            f.write('SB_EXTRA_ARGS=\"{args}\"\n'.format(args=" ".join(args)))

    def service_start(self, server, squeeze_mac, soundcard, name, timeout):
        self.write_environment_file(server, squeeze_mac, soundcard, name, timeout)
        expect_list = [r"Failed to start", "could not be found", pexpect.EOF, pexpect.TIMEOUT]
        result = pexpect.spawnu(f"systemctl restart -f squeezelite-custom").expect(expect_list, 4) == 2
        if result:
            print(f"Successfully started Squeezelite.")
        else:
            print(f"Failed to start Squeezelite.")
        return result

    @staticmethod
    def service_stop():
        expect_list = [r"Failed to stop", "could not be found", pexpect.EOF, pexpect.TIMEOUT]
        result = pexpect.spawnu(f"systemctl stop -f squeezelite-custom").expect(expect_list, 4) == 2
        if not result:
            expect_list = [r"Failed to kill", "could not be found", pexpect.EOF, pexpect.TIMEOUT]
            result = pexpect.spawnu(f"systemctl kill squeezelite-custom").expect(expect_list, 4) == 2
        if result:
            print(f"Successfully stopped Squeezelite.")
        else:
            print(f"Failed to stop Squeezelite.")
        return result
