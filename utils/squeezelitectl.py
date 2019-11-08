import pexpect
import logging


class SqueezeliteControll:
    @staticmethod
    def is_active():
        expect_list = [r"active \(running\)", r"inactive \(dead\)", "could not be found", "failed"]
        result = pexpect.spawnu(f"systemctl status squeezelite-custom").expect(expect_list) == 0
        return result

    @staticmethod
    def write_environment_file(server, squeeze_mac, soundcard, name, timeout):
        with open("./.squeezelite_env", "w") as f:
            args = [
                f"-s {server} -m {squeeze_mac}",
                f"-o {soundcard}",
                f"-n \'{name}\'",
            ]
            if timeout:
                args.append(f"-C {timeout}")
            f.write('SB_EXTRA_ARGS=\"{args}\"\n'.format(args=" ".join(args)))

    def service_start(self, server, squeeze_mac, soundcard, name, timeout):
        self.write_environment_file(server, squeeze_mac, soundcard, name, timeout)
        expect_list = [r"Failed to start", "could not be found", pexpect.EOF, pexpect.TIMEOUT]
        logging.debug("Trying to start/restart squeezelite...")
        result = pexpect.spawnu(f"systemctl restart -f squeezelite-custom").expect(expect_list, 4) == 2
        if result:
            logging.info(f"Successfully started Squeezelite.")
        else:
            logging.info(f"Failed to start Squeezelite.")
        return result

    @staticmethod
    def service_stop():
        expect_list = [r"Failed to stop", "could not be found", pexpect.EOF, pexpect.TIMEOUT]
        logging.debug("Trying to stop squeezelite...")
        result = pexpect.spawnu(f"systemctl stop -f squeezelite-custom").expect(expect_list, 4) == 2
        if not result:
            logging.debug("No success, trying to kill squeezelite...")
            expect_list = [r"Failed to kill", "could not be found", pexpect.EOF, pexpect.TIMEOUT]
            result = pexpect.spawnu(f"systemctl kill squeezelite-custom").expect(expect_list, 4) == 2
        if result:
            logging.info(f"Successfully stopped Squeezelite.")
        else:
            logging.info(f"Failed to stop Squeezelite.")
        return result
