import pexpect
import json


class SnapclientControll:
    def __init__(self):
        pass

    @staticmethod
    def is_active(soundcard):
        expect_list = [r"active \(running\)", r"inactive \(dead\)", "could not be found"]
        result = pexpect.spawnu(f"systemctl status snapclient@{soundcard}").expect(expect_list) == 0
        return result

    @staticmethod
    def write_environment_file(soundcard, latency, client_id):
        with open("/etc/default/snapclient", "w") as f:
            args = []
            if soundcard:
                args.append(f"-s {soundcard}")
            if latency:
                args.append(f"--latency {latency}")
            if client_id:
                args.append(f"--hostID {client_id}")
            f.write('SNAPCLIENT_OPTS="{args}"\n'.format(args=" ".join(args)))

    def start(self, client, userdata, msg):
        data = json.loads(msg.payload.decode("utf-8"))
        soundcard = data['soundcard']
        addr = data['addr']
        self.write_environment_file(soundcard, 0, addr)
        expect_list = [pexpect.EOF, r"not loaded", pexpect.TIMEOUT]
        result = pexpect.spawnu(f"systemctl restart -f snapclient@{soundcard}").expect(expect_list, 4) == 0
        if result:
            print(f"Successfully started Snapclient with soundcard <{soundcard}>.")
        else:
            print(f"Failed to start Snapclient with soundcard <{soundcard}>.")

    @staticmethod
    def stop(client, userdata, msg):
        data = json.loads(msg.payload.decode("utf-8"))
        soundcard = data['soundcard']
        expect_list = [pexpect.EOF, r"not loaded", pexpect.TIMEOUT]
        result = pexpect.spawnu(f"systemctl stop -f snapclient@{soundcard}").expect(expect_list, 4) == 0
        if result:
            print(f"Successfully stopped Snapclient with soundcard <{soundcard}>.")
        else:
            print(f"Failed to stop Snapclient with soundcard <{soundcard}>.")