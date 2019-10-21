import threading
import time
import json
import pexpect


class BluetoothHelper:
    """A wrapper for bluetoothctl utility."""
    # Based on ReachView code from Egor Fedorov (egor.fedorov@emlid.com)

    def __init__(self):
        self.process = pexpect.spawnu("bluetoothctl", echo=False, timeout=8)

    def send(self, command, pause=0):
        self.process.send(f"{command}\n")
        time.sleep(pause)
        self.process.expect([r"0;94m", pexpect.TIMEOUT, pexpect.EOF])

    def get_output(self, command):
        """Run a command in bluetoothctl prompt, return output as a list of lines."""
        self.send(command)
        return self.process.before.split("\r\n")

    def start_discover(self):
        """Start bluetooth scanning process."""
        self.process.send(f"scan off\n")
        expects = ["Failed to stop discovery", "Discovery stopped", pexpect.EOF, pexpect.TIMEOUT]
        self.process.expect(expects, 2)
        self.process.send(f"scan on\n")
        expects = ["Failed to start discovery", "Discovery started", pexpect.EOF, pexpect.TIMEOUT]
        res = self.process.expect(expects, 2)
        return res == 1

    def make_discoverable(self):
        """Make device discoverable."""
        self.send("discoverable on")

    @staticmethod
    def parse_device_info(info_string):
        """Parse a string corresponding to a device."""
        device = {}
        block_list = ["[\x1b[0;", "removed"]
        if not any(keyword in info_string for keyword in block_list):
            try:
                device_position = info_string.index("Device")
            except ValueError:
                pass
            else:
                if device_position > -1:
                    attribute_list = info_string[device_position:].split(" ", 2)
                    device = {
                        "mac_address": attribute_list[1],
                        "name": attribute_list[2],
                    }
        return device

    def wait_for_disconnect(self, addr):
        self.process.expect([f"{addr} Connected: no"], timeout=None)

    def get_available_devices(self):
        """Return a list of tuples of paired and discoverable devices."""
        available_devices = []
        out = self.get_output("devices")
        for line in out:
            device = self.parse_device_info(line)
            if device:
                available_devices.append(device)
        return available_devices

    def get_paired_devices(self):
        """Return a list of tuples of paired devices."""
        paired_devices = []
        out = self.get_output("paired-devices")
        for line in out:
            device = self.parse_device_info(line)
            if device:
                paired_devices.append(device)
        return paired_devices

    def get_discoverable_devices(self):
        """Filter paired devices out of available."""
        available = self.get_available_devices()
        paired = self.get_paired_devices()
        return [d for d in available if d not in paired]

    def get_device_info(self, mac_address):
        """Get device info by mac address."""
        out = self.get_output(f"info {mac_address}")
        return out

    def pair(self, mac_address):
        """Try to pair with a device by mac address."""
        self.send(f"pair {mac_address}", 4)
        res = self.process.expect(["Failed to pair", "Pairing successful", pexpect.EOF, pexpect.TIMEOUT])
        return res == 1

    def trust(self, mac_address):
        self.send(f"trust {mac_address}\n", 4)
        res = self.process.expect(["Failed to trust", "Trusted: yes", pexpect.EOF, pexpect.TIMEOUT])
        return res == 1

    def untrust(self, mac_address):
        self.send(f"untrust {mac_address}\n", 4)
        res = self.process.expect(["Failed to untrust", "untrust succeeded", pexpect.EOF, pexpect.TIMEOUT])
        return res == 1

    def remove(self, mac_address):
        """Remove paired device by mac address, return success of the operation."""
        self.send(f"remove {mac_address}\n", 3)
        res = self.process.expect(["not available", "Device has been removed", pexpect.EOF, pexpect.TIMEOUT])
        return res == 1

    def connect(self, mac_address):
        """Try to connect to a device by mac address."""
        self.process.send(f"connect {mac_address}\n")
        res = self.process.expect(["Failed to connect", "Connection successful", pexpect.TIMEOUT, pexpect.EOF], 6) == 1
        return res

    def is_connected(self, mac_address):
        self.process.send(f"info {mac_address}\n")
        res = self.process.expect(["Connected: no", "Connected: yes", pexpect.TIMEOUT, pexpect.EOF], 3) == 1
        return res

    def disconnect(self, mac_address):
        """Try to disconnect to a device by mac address."""
        self.process.send(f"disconnect {mac_address}\n")
        res = self.process.expect(["Failed to disconnect", "Connected: no", "Successful disconnected",
                                   pexpect.TIMEOUT, pexpect.EOF], 6) in [1, 2]
        return res


class Bluetooth:
    def __init__(self, mqtt_client, config):
        self.threadobjs = dict()
        self.threadobjs_wait_disconnect = dict()
        self.connected_devices = dict()
        self.bl_helper = BluetoothHelper()
        self.mqtt_client = mqtt_client
        self.site_id = config['snips']['device']['site_id']
        self.room_name = config['snips']['device']['room_name']
        self.synonyms = config['bluetooth']['synonyms']

    def thread_wait_until_disconnect(self, addr):
        while addr in self.connected_devices:
            time.sleep(5)
            if not self.bl_helper.is_connected(addr):
                del self.connected_devices[addr]
        #self.bl_helper.wait_for_disconnect(addr)
        #time.sleep(2)
        #if addr in self.connected_devices:
        #    del self.connected_devices[addr]
        self.send_device_lists()
        payload = {'siteId': self.site_id, 'result': True, 'addr': addr}
        self.mqtt_client.publish('bluetooth/answer/deviceDisconnect', payload=json.dumps(payload))

    def thread_discover(self):
        result = self.bl_helper.start_discover()
        payload = {'siteId': self.site_id, 'result': result}
        self.mqtt_client.publish('bluetooth/answer/devicesDiscover', payload=json.dumps(payload))
        if not result:
            return
        for i in range(30):
            time.sleep(1)
        self.send_device_lists()
        payload = {'discoverable_devices': self.bl_helper.get_discoverable_devices(),
                   'siteId': self.site_id}
        self.mqtt_client.publish('bluetooth/answer/devicesDiscovered', payload=json.dumps(payload))

    def thread_connect(self, addr):
        result = self.bl_helper.connect(addr)
        if result:
            if addr not in self.connected_devices:
                name = [d['name'] for d in self.bl_helper.get_available_devices() if d['mac_address'] == addr][0]
                self.connected_devices[addr] = name
            if addr not in self.threadobjs_wait_disconnect:
                self.threadobjs_wait_disconnect[addr] = threading.Thread(target=self.thread_wait_until_disconnect,
                                                                         args=(addr,))
                self.threadobjs_wait_disconnect[addr].start()
        payload = {'siteId': self.site_id, 'result': result, 'addr': addr}
        self.mqtt_client.publish('bluetooth/answer/deviceConnect', payload=json.dumps(payload))
        self.send_device_lists()

    def thread_disconnect(self, addr):
        result = self.bl_helper.disconnect(addr)
        if result:
            if addr in self.connected_devices:
                del self.connected_devices[addr]
            if addr in self.threadobjs_wait_disconnect:
                del self.threadobjs_wait_disconnect[addr]
        payload = {'siteId': self.site_id, 'result': result, 'addr': addr}
        self.mqtt_client.publish('bluetooth/answer/deviceDisconnect', payload=json.dumps(payload))
        self.send_device_lists()

    def thread_remove(self, addr):
        result = self.bl_helper.remove(addr)
        if result:
            if addr in self.connected_devices:
                del self.connected_devices[addr]
            if addr in self.threadobjs_wait_disconnect:
                del self.threadobjs_wait_disconnect[addr]
        payload = {'siteId': self.site_id, 'result': result, 'addr': addr}
        self.mqtt_client.publish('bluetooth/answer/deviceRemove', payload=json.dumps(payload))
        self.send_device_lists()

    def msg_discover(self, client, userdata, msg):
        if 'discover' in self.threadobjs:
            del self.threadobjs['discover']
        self.threadobjs['discover'] = threading.Thread(target=self.thread_discover)
        self.threadobjs['discover'].start()

    def msg_connect(self, client, userdata, msg):
        data = json.loads(msg.payload.decode("utf-8"))
        self.connect(data['addr'])

    def connect(self, addr):
        if 'connect' in self.threadobjs:
            del self.threadobjs['connect']
        self.threadobjs['connect'] = threading.Thread(target=self.thread_connect, args=(addr,))
        self.threadobjs['connect'].start()

    def connect_with_block(self, addr):
        result = self.bl_helper.connect(addr)
        if result:
            if addr not in self.connected_devices:
                name = [d['name'] for d in self.bl_helper.get_available_devices() if d['mac_address'] == addr][0]
                self.connected_devices[addr] = name
            if addr not in self.threadobjs_wait_disconnect:
                self.threadobjs_wait_disconnect[addr] = threading.Thread(target=self.thread_wait_until_disconnect,
                                                                         args=(addr,))
                self.threadobjs_wait_disconnect[addr].start()
        self.send_device_lists()
        return result

    def msg_disconnect(self, client, userdata, msg):
        data = json.loads(msg.payload.decode("utf-8"))
        if 'disconnect' in self.threadobjs:
            del self.threadobjs['disconnect']
        self.threadobjs['disconnect'] = threading.Thread(target=self.thread_disconnect, args=(data['addr'],))
        self.threadobjs['disconnect'].start()

    def msg_remove(self, client, userdata, msg):
        data = json.loads(msg.payload.decode("utf-8"))
        if 'remove' in self.threadobjs:
            del self.threadobjs['remove']
        self.threadobjs['remove'] = threading.Thread(target=self.thread_remove, args=(data['addr'],))
        self.threadobjs['remove'].start()

    def msg_send_device_lists(self, client, userdata, msg):
        self.send_device_lists()

    def msg_send_site_info(self, client, userdata, msg):
        self.send_site_info()

    def send_device_lists(self):
        payload = {'available_devices': self.bl_helper.get_available_devices(),
                   'paired_devices': self.bl_helper.get_paired_devices(),
                   'connected_devices': [{'mac_address': addr, 'name': self.connected_devices[addr]}
                                         for addr in self.connected_devices],
                   'siteId': self.site_id}
        self.mqtt_client.publish('bluetooth/answer/deviceLists', payload=json.dumps(payload))

    def send_site_info(self):
        payload = {'room_name': self.room_name, 'site_id': self.site_id, 'synonyms': self.synonyms}
        self.mqtt_client.publish('bluetooth/answer/siteInfo', payload=json.dumps(payload))
