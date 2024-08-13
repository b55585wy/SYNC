import multiprocessing
import serial
import serial.tools.list_ports
import time
from multiprocessing import Queue


class SerialDevice:
    def __init__(self, port='COM3', baudrate=115200, timeout=1, data_queue=None):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.device_types = {
            0xC0: "血压（HKB-08B V2.0）",
            0xC3: "胃肠电：HKV-15/2D",
            0xC4: "皮温：HKT-09B",
            0xC5: "皮肤电阻：HKR-11C",
            0xC6: "肌电：HKJ-15C",
            0xC7: "血氧：HKS-12C",
            0xC8: "心率：HKX-08C",
            0xC9: "体温：HKT-09A",
            0xCA: "脉搏：HK-2000C",
            0xCB: "红外脉搏：HKG-07C",
            0xCC: "呼吸：HKH-11C",
            0xCD: "血压：HKB-08B",
            0xCE: "心电：HKD-10C",
            0xB1: "心音（HKY-06C）"
        }
        self.ser = None
        self.data_queue = data_queue if data_queue else Queue()

    @staticmethod
    def list_available_ports():
        ports = serial.tools.list_ports.comports()
        available_ports = [port.device for port in ports]
        print("Available Ports:", available_ports)
        return available_ports

    def open_serial_port(self):
        try:
            self.ser = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                bytesize=serial.EIGHTBITS
            )
            print("Serial port opened successfully")
        except serial.SerialException as e:
            print(f"Failed to open serial port: {e}")
            self.ser = None  # 设置错误标志，之后在调用处检查这个标志

    @staticmethod
    def calculate_checksum(data):
        return sum(data) & 0xFF

    def send_command(self, command):
        checksum = self.calculate_checksum(command[2:])
        command.insert(3, checksum)
        self.ser.write(bytearray(command))

    def send_start_measurement(self):
        command = [0xFF, 0xCC, 0x03, 0xA0]
        self.send_command(command)

    def send_stop_measurement(self):
        command = [0xFF, 0xCC, 0x03, 0xA1]
        self.send_command(command)

    def adjust_breath_amplitude(self, level):
        command = [0xFF, 0xCC, 0x04, 0xA4, level]
        self.send_command(command)

    def parse_serial_data(self, data):
        if len(data) < 7 or data[0] != 0xFF:
            print("Invalid data length or header, discarding:", data)
            return None
        data_length = data[2]
        if len(data) < data_length + 2:
            print("Insufficient data length, discarding:", data)
            return None
        checksum = self.calculate_checksum([data[2]] + data[4:])
        if data[3] != checksum:
            print("Checksum failed, discarding:", data)
            return None
        value = 0
        for i in range(5, len(data)):
            value = (value << 8) | data[i]
        return {
            'device_type': self.device_types.get(data[1], 'Unknown Device'),
            'command': data[4],
            'parameters': data[5:data_length + 2],
            'value': value
        }

    def collect_data(self):
        self.open_serial_port()  # 确保串口已经打开
        self.send_stop_measurement()
        self.adjust_breath_amplitude(5)
        self.send_start_measurement()

        start_time = time.time()
        buffer = []

        try:
            while True:
                while self.ser.in_waiting:
                    byte = self.ser.read(1)
                    if byte:
                        buffer.append(ord(byte))
                        if len(buffer) >= 7 and buffer[0] == 0xFF:
                            data_length = buffer[2]
                            if len(buffer) >= data_length + 2:
                                packet = buffer[:data_length + 2]
                                buffer = buffer[data_length + 2:]
                                parsed_data = self.parse_serial_data(packet)
                                if parsed_data:
                                    # print(f"{parsed_data}")
                                    time_interval = time.time() - start_time
                                    self.data_queue.put({
                                        'timestamp': time_interval,
                                        'data': parsed_data['value']
                                    })
                time.sleep(0.01)

        except Exception as e:
            print(f"Error reading serial data: {e}")
        finally:
            self.send_stop_measurement()

    def get_data_from_queue(self):
        if not self.data_queue.empty():
            return self.data_queue.get()
        return None