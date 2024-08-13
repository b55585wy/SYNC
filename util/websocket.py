import asyncio
import json
import websockets

class WebSocketServer:
    def __init__(self, host='localhost', port=8765, serial_device=None):
        self.host = host
        self.port = port
        self.device = serial_device

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
