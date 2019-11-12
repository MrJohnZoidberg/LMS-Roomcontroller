import threading
import time
import json
import pexpect
import logging


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
        time.sleep(1)
        self.process.send(f"scan on\n")
        expects = ["Failed to start discovery", "Discovery started", pexpect.EOF, pexpect.TIMEOUT]
        res = self.process.expect(expects, 2)
        return res == 1

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

    def remove(self, mac_address):
        """Remove paired device by mac address, return success of the operation."""
        self.process.send(f"remove {mac_address}\n")
        res = self.process.expect(["not available", "Device has been removed", pexpect.EOF, pexpect.TIMEOUT], 7)
        return res == 1

    def connect(self, mac_address):
        """Try to connect to a device by mac address."""
        self.process.send(f"connect {mac_address}\n")
        expects = ["Failed to connect", "Connection successful", "not available", pexpect.TIMEOUT, pexpect.EOF]
        res = self.process.expect(expects, 7)
        return res == 1

    def is_connected(self, mac_address):
        self.process.send(f"info {mac_address}\n")
        expects = ["Connected: no", "Connected: yes", "not available", pexpect.TIMEOUT, pexpect.EOF]
        res = self.process.expect(expects, 4)
        self.process.expect([r"0;94m", pexpect.TIMEOUT, pexpect.EOF])
        return res == 1

    def disconnect(self, mac_address):
        """Try to disconnect to a device by mac address."""
        self.process.send(f"disconnect {mac_address}\n")
        expects = ["Failed to disconnect", "not available", "Connected: no",
                   "Successful disconnected", pexpect.TIMEOUT, pexpect.EOF]
        res = self.process.expect(expects, 6)
        return res == 2 or res == 3


class Bluetooth:
    def __init__(self, mqtt_client, config):
        self.threadobjs = dict()
        self.threadobjs_wait_disconnect = dict()
        self.connected_devices = dict()
        self.bl_helper = BluetoothHelper()
        self.mqtt_client = mqtt_client
        self.site_id = config['snips']['site']['site_id']
        self.room_name = config['snips']['site']['room_name']
        self.devices_names = [item for item in config['devices'] if not isinstance(config['devices'][item], dict)]
        self.devices_names = {item: config['devices'][item] for item in config['devices']
                              if not isinstance(config['devices'][item], dict)}
        self.fill_connected_devices()
        self.send_blt_info()

    def fill_connected_devices(self):
        for d in self.bl_helper.get_paired_devices():
            addr = d['mac_address']
            if self.bl_helper.is_connected(addr):
                self.connected_devices[addr] = d['name']
                if addr not in self.threadobjs_wait_disconnect:
                    thread_obj = threading.Thread(target=self.thread_wait_until_disconnect, args=(addr,))
                    self.threadobjs_wait_disconnect[addr] = thread_obj
                    self.threadobjs_wait_disconnect[addr].start()
            time.sleep(0.2)

    def thread_wait_until_disconnect(self, addr):
        connected = True
        while connected:
            time.sleep(10)
            if not self.bl_helper.is_connected(addr):
                connected = False
            logging.debug(f"({addr}) connected: {connected}")
        if addr in self.connected_devices:
            del self.connected_devices[addr]
            payload = {
                'siteId': self.site_id,
                'result': True,
                'addr': addr
            }
            self.mqtt_client.publish('bluetooth/answer/deviceDisconnect', payload=json.dumps(payload))
            self.send_blt_info()
        if addr in self.threadobjs_wait_disconnect:
            del self.threadobjs_wait_disconnect[addr]

    def thread_discover(self):
        result = self.bl_helper.start_discover()
        payload = {'siteId': self.site_id, 'result': result}
        self.mqtt_client.publish('bluetooth/answer/devicesDiscover', payload=json.dumps(payload))
        if not result:
            return
        for i in range(30):
            time.sleep(1)
        payload = {
            'discoverable_devices': self.bl_helper.get_discoverable_devices(),
            'siteId': self.site_id
        }
        self.mqtt_client.publish('bluetooth/answer/devicesDiscovered', payload=json.dumps(payload))
        self.send_blt_info()

    def thread_connect(self, addr, tries):

        result = self.bl_helper.connect(addr)
        if not result and tries > 1:
            for i in range(tries-1):
                result = self.bl_helper.connect(addr)
                if result:
                    break

        if result:
            if addr not in self.connected_devices:
                name = [d['name'] for d in self.bl_helper.get_available_devices() if d['mac_address'] == addr][0]
                self.connected_devices[addr] = name
            if addr not in self.threadobjs_wait_disconnect:
                thread_obj = threading.Thread(target=self.thread_wait_until_disconnect, args=(addr,))
                self.threadobjs_wait_disconnect[addr] = thread_obj
                self.threadobjs_wait_disconnect[addr].start()

        payload = {
            'siteId': self.site_id,
            'result': result,
            'addr': addr
        }
        self.mqtt_client.publish(f'bluetooth/answer/deviceConnect', payload=json.dumps(payload))
        self.send_blt_info()

    def thread_disconnect(self, addr):

        result = self.bl_helper.disconnect(addr)
        if result:
            if addr in self.connected_devices:
                del self.connected_devices[addr]
            if addr in self.threadobjs_wait_disconnect:
                del self.threadobjs_wait_disconnect[addr]

        payload = {
            'siteId': self.site_id,
            'result': result,
            'addr': addr
        }
        self.mqtt_client.publish('bluetooth/answer/deviceDisconnect', payload=json.dumps(payload))
        self.send_blt_info()

    def thread_remove(self, addr):

        result = self.bl_helper.remove(addr)
        if result:
            if addr in self.connected_devices:
                del self.connected_devices[addr]
            if addr in self.threadobjs_wait_disconnect:
                del self.threadobjs_wait_disconnect[addr]

        payload = {
            'siteId': self.site_id,
            'result': result,
            'addr': addr
        }
        self.mqtt_client.publish('bluetooth/answer/deviceRemove', payload=json.dumps(payload))
        self.send_blt_info()

    def msg_discover(self, client, userdata, msg):
        if 'discover' in self.threadobjs:
            del self.threadobjs['discover']
        self.threadobjs['discover'] = threading.Thread(target=self.thread_discover)
        self.threadobjs['discover'].start()

    def msg_connect(self, client, userdata, msg):
        data = json.loads(msg.payload.decode("utf-8"))
        if data.get('tries'):
            self.connect(data['addr'], int(data['tries']))
        else:
            self.connect(data['addr'])

    def connect(self, addr, tries=0):
        if 'connect' in self.threadobjs:
            del self.threadobjs['connect']
        self.threadobjs['connect'] = threading.Thread(target=self.thread_connect, args=(addr, tries,))
        self.threadobjs['connect'].start()

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

    def msg_send_blt_info(self, client, userdata, msg):
        self.send_blt_info()

    def send_blt_info(self):
        available_devices = self.bl_helper.get_available_devices()
        payload = {
            'room_name': self.room_name,
            'site_id': self.site_id,
            'device_names': self.devices_names,
            'available_devices': available_devices,
            'paired_devices': self.bl_helper.get_paired_devices(),
            'connected_devices': [d for d in available_devices if d['mac_address'] in self.connected_devices]
        }
        self.mqtt_client.publish('bluetooth/answer/siteInfo', payload=json.dumps(payload))
