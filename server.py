import asyncio
import websockets
import json
import random
import string
import os

rooms = {}

def make_code():
    chars = string.ascii_uppercase + string.digits
    while True:
        code = ''.join(random.choices(chars, k=4))
        if any(c.isalpha() for c in code) and any(c.isdigit() for c in code):
            return code

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
                    print(f"Room created: {room_code}", flush=True)
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
                        print(f"Room joined: {room_code}", flush=True)
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
                print(f"Message error: {e}", flush=True)
    except websockets.exceptions.ConnectionClosed:
        pass
    except Exception as e:
        print(f"Handler error: {e}", flush=True)
    finally:
        if room_code and room_code in rooms:
            room = rooms[room_code]
            other = room["guest"] if ws == room["host"] else room["host"]
            if other:
                try:
                    await other.send(json.dumps({"type":"opponent_left"}))
                except:
                    pass
            del rooms[room_code]
            print(f"Room closed: {room_code}", flush=True)

async def health_check(path, request_headers):
    if path == "/health":
        return websockets.http11.Response(
            200, "OK",
            websockets.datastructures.Headers([
                ("Content-Type", "text/plain")]),
            b"ECHOES RELAY ONLINE")

async def main():
    port = int(os.environ.get("PORT", 8765))
    print(f"Starting relay on port {port}", flush=True)
    async with websockets.serve(
            handler, "0.0.0.0", port,
            process_request=health_check):
        print(f"Relay running!", flush=True)
        await asyncio.Future()

asyncio.run(main())
