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
            data = json.loads(message)
            if data["type"] == "create":
                room_code = make_code()
                rooms[room_code] = {"host": ws, "guest": None}
                await ws.send(json.dumps({"type":"created","code":room_code}))
            elif data["type"] == "join":
                room_code = data["code"].upper()
                if room_code not in rooms:
                    await ws.send(json.dumps({"type":"error","msg":"ROOM NOT FOUND"}))
                elif rooms[room_code]["guest"] is not None:
                    await ws.send(json.dumps({"type":"error","msg":"ROOM FULL"}))
                else:
                    rooms[room_code]["guest"] = ws
                    host = rooms[room_code]["host"]
                    await ws.send(json.dumps({"type":"joined","code":room_code}))
                    await host.send(json.dumps({"type":"opponent_joined"}))
            elif data["type"] == "game_data":
                if room_code and room_code in rooms:
                    room = rooms[room_code]
                    target = room["guest"] if ws == room["host"] else room["host"]
                    if target:
                        await target.send(message)
            elif data["type"] == "ping":
                await ws.send(json.dumps({"type":"pong"}))
    except:
        pass
    finally:
        if room_code and room_code in rooms:
            del rooms[room_code]

async def main():
    port = int(os.environ.get("PORT", 8765))
    async with websockets.serve(handler, "0.0.0.0", port):
        print(f"Relay server running on port {port}")
        await asyncio.Future()

asyncio.run(main())
