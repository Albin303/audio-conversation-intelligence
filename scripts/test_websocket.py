import asyncio
import websockets
import json

async def test_live_audio_stream():
    uri = "ws://localhost:8000/api/stream"
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected to Live Audio WebSocket.")
            
            # Simulate streaming audio chunks (e.g., 5 seconds of audio)
            for i in range(5):
                # Send dummy binary data representing an audio PCM chunk
                dummy_chunk = b"\\x00\\x01" * 1024  # 2KB chunk
                await websocket.send(dummy_chunk)
                
                # Receive the status/response from the server
                response = await websocket.recv()
                data = json.loads(response)
                print(f"Chunk {i+1} Sent. Server Response: {data}")
                
                # Wait a bit before sending the next chunk, simulating live speed
                await asyncio.sleep(1)
                
            print("Finished sending live stream chunks.")
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_live_audio_stream())
