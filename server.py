import asyncio
import websockets
import json
import random
import string
import os
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler

rooms = {}

def make_code():
    chars = string.ascii_uppercase + string.digits
    while True:
        code = ''.join(random.choices(chars, k=4))
        if any(c.isalpha() for c in code) and any(c.isdigit() for c in code):
            return code

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ECHOES RELAY ONLINE")
    def log_message(self, *args):
        pass

async def handler(ws):
    room_code = None
    try:
        async for message in ws:
            try:
                data = json.loads(message)
                msg_type = data.get("type")
                if msg_type == "create":
                    room_code = make_code()
                    rooms[room_code] = {"host": ws, "guest": None}
                    await ws.send(json.dumps({"type":"created","code":room_code}))
                    print(f"Room created: {room_code}")
                elif msg_type == "join":
                    code = data["code"].upper()
                    if code not in rooms:
                        await ws.send(json.dumps({"type":"error","msg":"ROOM NOT FOUND"}))
                    elif rooms[code]["guest"] is not None:
                        await ws.send(json.dumps({"type":"error","msg":"ROOM FULL"}))
                    else:
                        room_code = code
                        rooms[room_code]["guest"] = ws
                        host = rooms[room_code]["host"]
                        await ws.send(json.dumps({"type":"joined","code":room_code}))
                        await host.send(json.dumps({"type":"opponent_joined"}))
                        print(f"Room joined: {room_code}")
                elif msg_type == "game_data":
                    if room_code and room_code in rooms:
                        room = rooms[room_code]
                        target = room["guest"] if ws == room["host"] else room["host"]
                        if target:
                            try:
                                await target.send(message)
                            except:
                                pass
                elif msg_type == "ping":
                    await ws.send(json.dumps({"type":"pong"}))
                elif msg_type == "leave":
                    break
            except json.JSONDecodeError:
                pass
            except Exception as e:
                print(f"Message error: {e}")
    except websockets.exceptions.ConnectionClosed:
        pass
    except Exception as e:
        print(f"Handler error: {e}")
    finally:
        if room_code and room_code in rooms:
            room = rooms[room_code]
            other = None
            if ws == room["host"]:
                other = room["guest"]
            elif ws == room["guest"]:
                other = room["host"]
            if other:
                try:
                    await other.send(json.dumps({"type":"opponent_left"}))
                except:
                    pass
            del rooms[room_code]
            print(f"Room closed: {room_code}")

async def websocket_main():
    port = int(os.environ.get("PORT", 8765))
    print(f"WebSocket relay running on port {port}")
    async with websockets.serve(handler, "0.0.0.0", port):
        await asyncio.Future()

def run_health_server():
    server = HTTPServer(("0.0.0.0", 8080), HealthHandler)
    server.serve_forever()

if __name__ == "__main__":
    health_thread = Thread(target=run_health_server, daemon=True)
    health_thread.start()
    print("Health check server on port 8080")
    asyncio.run(websocket_main())
