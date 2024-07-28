import asyncio
import time

from bleak import BleakScanner, BleakClient

async def scan_and_connect():
    # scan the device
    devices = await BleakScanner.discover()
    for device in devices:
        print(device)

    # 假设我们知道设备的MAC地址
    # address = "你的心率带MAC地址"  # 替换为实际的MAC地址
    # async with BleakClient(address) as client:
    #     print(f"Connected: {client.is_connected}")
#     D0:A4:69:B6:8F:A2
    address = "D0:A4:69:B6:8F:A2"  # 替换为实际的MAC地址
    async with BleakClient(address) as client:
        print(f"Connected: {client.is_connected}")
asyncio.run(scan_and_connect())

import asyncio
from bleak import BleakClient

HEART_RATE_SERVICE_UUID = "0000180d-0000-1000-8000-00805f9b34fb"
HEART_RATE_MEASUREMENT_UUID = "00002a37-0000-1000-8000-00805f9b34fb"

def notification_handler(sender, data):
    # 处理心率数据
    heart_rate = data[1]
    print(f"Heart Rate: {heart_rate}")

async def run(address):
    async with BleakClient(address) as client:
        await client.start_notify(HEART_RATE_MEASUREMENT_UUID, notification_handler)
        await asyncio.sleep(600)  # 订阅600秒
        await client.stop_notify(HEART_RATE_MEASUREMENT_UUID)

address = "D0:A4:69:B6:8F:A2"  # 替换为实际的MAC地址
asyncio.run(run(address))