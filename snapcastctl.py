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

    def service_start(self, soundcard, latency, client_id):
        self.write_environment_file(soundcard, latency, client_id)
        expect_list = [pexpect.EOF, r"not loaded", pexpect.TIMEOUT]
        result = pexpect.spawnu(f"systemctl restart -f snapclient@{soundcard}").expect(expect_list, 4) == 0
        if result:
            print(f"Successfully started Snapclient with soundcard <{soundcard}>.")
        else:
            print(f"Failed to start Snapclient with soundcard <{soundcard}>.")
        return result

    def service_stop(self, soundcard):
        expect_list = [pexpect.EOF, r"not loaded", pexpect.TIMEOUT]
        result = pexpect.spawnu(f"systemctl stop -f snapclient@{soundcard}").expect(expect_list, 4) == 0
        if result:
            print(f"Successfully stopped Snapclient with soundcard <{soundcard}>.")
        else:
            print(f"Failed to stop Snapclient with soundcard <{soundcard}>.")
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


class SnapcastControll:
    def __init__(self, mqtt_client, config):
        self.mqtt_client = mqtt_client
        self.site_id = config['snips']['device']['site_id']
        self.room_name = config['snips']['device']['room_name']
        self.snapclientctl = SnapclientControll()
        self.snapserverctl = SnapserverControll()
        self.config = config

    @staticmethod
    def set_volume(slot_dict):
        url = f"http:///jsonrpc"
        headers = {'content-type': 'application/json'}
        # Example echo method
        payload = {"id": 8, "jsonrpc": "2.0", "method": "Client.GetStatus", "params": {"id": "b8:27:eb:65:d2:48"}}
        #response = requests.post(url, data=json.dumps(payload), headers=headers).json()
        #print(response)
