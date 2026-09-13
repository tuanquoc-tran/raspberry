import asyncio
import json
import websockets

async def handler(websocket):
    print(f"✅ ESP32 connected from: {websocket.remote_address}")
    try:
        async for message in websocket:
            print(f"📩 Received from ESP32: {message}")
            data = json.loads(message)
            
            # Xử lý lệnh test
            if data.get("action") == "ping":
                response = {"status": "success", "message": "Pong from RaspFlip Pi!"}
                await websocket.send(json.dumps(response))
                print("📤 Sent response to ESP32")
    except websockets.ConnectionClosed:
        print("❌ ESP32 disconnected")

async def main():
    # Lắng nghe trên 0.0.0.0 cổng 8765
    async with websockets.serve(handler, "0.0.0.0", 8765):
        print("🚀 WS Server listening on port 8765...")
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())