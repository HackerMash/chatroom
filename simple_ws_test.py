#!/usr/bin/env python3
"""
Simple WebSocket connection test
"""

import asyncio
import websockets
import json
import uuid
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv('/app/frontend/.env')

BACKEND_URL = os.getenv('REACT_APP_BACKEND_URL', 'http://localhost:8001')
WS_BASE_URL = BACKEND_URL.replace('https://', 'wss://').replace('http://', 'ws://')

async def test_simple_websocket():
    user_id = str(uuid.uuid4())
    username = "TestUser"
    room_id = "test-room"
    
    ws_url = f"{WS_BASE_URL}/ws/{room_id}/{user_id}/{username}"
    
    print(f"Attempting to connect to: {ws_url}")
    
    try:
        # Try with a longer timeout
        async with websockets.connect(ws_url, timeout=10) as websocket:
            print("✅ WebSocket connection successful!")
            
            # Send a test message
            test_message = {"message": "Hello WebSocket!"}
            await websocket.send(json.dumps(test_message))
            print("✅ Message sent successfully!")
            
            # Try to receive a response
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                print(f"✅ Received response: {response}")
                return True
            except asyncio.TimeoutError:
                print("⚠️ Timeout waiting for response, but connection worked")
                return True
                
    except Exception as e:
        print(f"❌ WebSocket connection failed: {str(e)}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_simple_websocket())
    print(f"Test result: {'PASS' if success else 'FAIL'}")