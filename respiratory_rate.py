import serial
import serial.tools.list_ports
import time
import asyncio
import websockets
import threading
from queue import Queue
import json

class SerialDevice:
    def __init__(self, port='COM2', baudrate=115200, timeout=1):
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
        self.data_queue = Queue()

    @staticmethod
    def list_available_ports():
        ports = serial.tools.list_ports.comports()
        available_ports = [port.device for port in ports]
        print("可用的串口：", available_ports)
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
            print("串口打开成功")
        except serial.SerialException as e:
            print(f"无法打开串口: {e}")
            exit()

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
            print("数据长度不足或帧头不对，丢弃：", data)
            return None
        data_length = data[2]
        if len(data) < data_length + 2:
            print("数据长度不足，丢弃：", data)
            return None
        checksum = self.calculate_checksum([data[2]] + data[4:])
        if data[3] != checksum:
            print("校验失败，丢弃：", data)
            return None
        value = 0
        for i in range(5, len(data)):
            value = (value << 8) | data[i]
        return {
            'device_type': self.device_types.get(data[1], '未知设备'),
            'command': data[4],
            'parameters': data[5:data_length + 2],
            'value': value
        }

    def collect_data(self):
        self.send_stop_measurement()
        self.adjust_breath_amplitude(5)
        self.send_start_measurement()

        start_time = time.time()
        buffer = []

        try:
            while True:
                if self.ser.in_waiting:
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
                                    print(f"{parsed_data}")
                                    self.data_queue.put({
                                        'timestamp': time.time() - start_time,
                                        'data': parsed_data
                                    })
        except Exception as e:
            print(f"读取串口数据时出错: {e}")
        finally:
            self.send_stop_measurement()

    def get_data_from_queue(self):
        if not self.data_queue.empty():
            return self.data_queue.get()
        return None


class WebSocketServer:
    def __init__(self, host='localhost', port=8765):
        self.host = host
        self.port = port
        self.device = SerialDevice(port='COM2')

    async def handler(self, websocket, path):
        print("WebSocket connection opened")
        try:
            while True:
                data = self.device.get_data_from_queue()
                if data:
                    await websocket.send(json.dumps(data))
                await asyncio.sleep(0.01)
        except websockets.exceptions.ConnectionClosed:
            print("WebSocket connection closed")

    def start_server(self):
        start_server = websockets.serve(self.handler, self.host, self.port)
        loop = asyncio.get_event_loop()
        loop.run_until_complete(start_server)
        print(f"WebSocket server started at ws://{self.host}:{self.port}")
        try:
            loop.run_forever()
        except KeyboardInterrupt:
            print("Server stopped by user")
        finally:
            tasks = asyncio.all_tasks(loop)
            for task in tasks:
                task.cancel()
            loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))
            loop.close()

    def start_serial_device(self):
        self.device.open_serial_port()
        data_thread = threading.Thread(target=self.device.collect_data)
        data_thread.start()


if __name__ == "__main__":
    ws_server = WebSocketServer()
    ws_server.device.list_available_ports()
    ws_server.start_serial_device()  # 启动串口数据采集
    ws_server.start_server()         # 启动WebSocket服务器
