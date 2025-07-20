#!/usr/bin/env python3
"""
Backend Testing Suite for Lofi Chatroom Application
Tests REST API endpoints, WebSocket functionality, and database operations
"""

import asyncio
import json
import requests
import websockets
import uuid
from datetime import datetime
import time
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv('/app/frontend/.env')

# Get backend URL from frontend environment
BACKEND_URL = os.getenv('REACT_APP_BACKEND_URL', 'http://localhost:8001')
API_BASE_URL = f"{BACKEND_URL}/api"
WS_BASE_URL = BACKEND_URL.replace('https://', 'wss://').replace('http://', 'ws://')

print(f"Testing backend at: {API_BASE_URL}")
print(f"WebSocket URL: {WS_BASE_URL}")

class BackendTester:
    def __init__(self):
        self.test_results = []
        self.session = requests.Session()
        
    def log_test(self, test_name, success, message="", details=None):
        """Log test results"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {message}")
        
        self.test_results.append({
            'test': test_name,
            'success': success,
            'message': message,
            'details': details,
            'timestamp': datetime.now().isoformat()
        })
        
    def test_root_endpoint(self):
        """Test GET /api/ endpoint"""
        try:
            response = self.session.get(f"{API_BASE_URL}/")
            if response.status_code == 200:
                data = response.json()
                if "message" in data:
                    self.log_test("Root Endpoint", True, f"Response: {data}")
                    return True
                else:
                    self.log_test("Root Endpoint", False, "Missing 'message' field in response")
                    return False
            else:
                self.log_test("Root Endpoint", False, f"HTTP {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_test("Root Endpoint", False, f"Connection error: {str(e)}")
            return False
    
    def test_init_default_rooms(self):
        """Test POST /api/init-default-rooms endpoint"""
        try:
            response = self.session.post(f"{API_BASE_URL}/init-default-rooms")
            if response.status_code == 200:
                data = response.json()
                if "message" in data and "initialized" in data["message"]:
                    self.log_test("Initialize Default Rooms", True, f"Response: {data}")
                    return True
                else:
                    self.log_test("Initialize Default Rooms", False, f"Unexpected response: {data}")
                    return False
            else:
                self.log_test("Initialize Default Rooms", False, f"HTTP {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_test("Initialize Default Rooms", False, f"Error: {str(e)}")
            return False
    
    def test_get_rooms(self):
        """Test GET /api/rooms endpoint"""
        try:
            response = self.session.get(f"{API_BASE_URL}/rooms")
            if response.status_code == 200:
                rooms = response.json()
                if isinstance(rooms, list) and len(rooms) > 0:
                    # Check if rooms have required fields
                    required_fields = ['id', 'name', 'description', 'niche', 'user_count']
                    first_room = rooms[0]
                    missing_fields = [field for field in required_fields if field not in first_room]
                    
                    if not missing_fields:
                        self.log_test("Get Rooms", True, f"Found {len(rooms)} rooms with proper structure")
                        return rooms
                    else:
                        self.log_test("Get Rooms", False, f"Missing fields in room object: {missing_fields}")
                        return None
                else:
                    self.log_test("Get Rooms", False, "No rooms found or invalid response format")
                    return None
            else:
                self.log_test("Get Rooms", False, f"HTTP {response.status_code}: {response.text}")
                return None
        except Exception as e:
            self.log_test("Get Rooms", False, f"Error: {str(e)}")
            return None
    
    def test_get_room_messages(self, room_id):
        """Test GET /api/rooms/{room_id}/messages endpoint"""
        try:
            response = self.session.get(f"{API_BASE_URL}/rooms/{room_id}/messages")
            if response.status_code == 200:
                messages = response.json()
                if isinstance(messages, list):
                    self.log_test("Get Room Messages", True, f"Retrieved {len(messages)} messages for room {room_id}")
                    return messages
                else:
                    self.log_test("Get Room Messages", False, "Invalid response format - expected list")
                    return None
            else:
                self.log_test("Get Room Messages", False, f"HTTP {response.status_code}: {response.text}")
                return None
        except Exception as e:
            self.log_test("Get Room Messages", False, f"Error: {str(e)}")
            return None
    
    def test_create_custom_room(self):
        """Test POST /api/rooms endpoint"""
        try:
            test_room = {
                "name": "🧪 Test Room",
                "description": "A test room for backend testing",
                "niche": "testing"
            }
            
            response = self.session.post(f"{API_BASE_URL}/rooms", json=test_room)
            if response.status_code == 200:
                room = response.json()
                required_fields = ['id', 'name', 'description', 'niche']
                missing_fields = [field for field in required_fields if field not in room]
                
                if not missing_fields:
                    self.log_test("Create Custom Room", True, f"Created room with ID: {room['id']}")
                    return room
                else:
                    self.log_test("Create Custom Room", False, f"Missing fields in response: {missing_fields}")
                    return None
            else:
                self.log_test("Create Custom Room", False, f"HTTP {response.status_code}: {response.text}")
                return None
        except Exception as e:
            self.log_test("Create Custom Room", False, f"Error: {str(e)}")
            return None

    async def test_websocket_connection(self, room_id):
        """Test WebSocket connection and basic messaging"""
        user_id = str(uuid.uuid4())
        username = "TestUser"
        
        ws_url = f"{WS_BASE_URL}/ws/{room_id}/{user_id}/{username}"
        
        try:
            async with websockets.connect(ws_url) as websocket:
                # Test connection established
                self.log_test("WebSocket Connection", True, f"Connected to room {room_id}")
                
                # Send a test message
                test_message = {
                    "message": "Hello from backend test! 🎵"
                }
                
                await websocket.send(json.dumps(test_message))
                
                # Wait for response (should be the broadcasted message)
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    message_data = json.loads(response)
                    
                    if message_data.get("type") == "message" and message_data.get("message") == test_message["message"]:
                        self.log_test("WebSocket Messaging", True, "Message sent and received successfully")
                        return True
                    else:
                        self.log_test("WebSocket Messaging", False, f"Unexpected message format: {message_data}")
                        return False
                        
                except asyncio.TimeoutError:
                    self.log_test("WebSocket Messaging", False, "Timeout waiting for message response")
                    return False
                    
        except Exception as e:
            self.log_test("WebSocket Connection", False, f"Connection error: {str(e)}")
            return False

    async def test_websocket_user_notifications(self, room_id):
        """Test WebSocket user join/leave notifications"""
        user_id_1 = str(uuid.uuid4())
        user_id_2 = str(uuid.uuid4())
        username_1 = "TestUser1"
        username_2 = "TestUser2"
        
        ws_url_1 = f"{WS_BASE_URL}/ws/{room_id}/{user_id_1}/{username_1}"
        ws_url_2 = f"{WS_BASE_URL}/ws/{room_id}/{user_id_2}/{username_2}"
        
        try:
            # Connect first user
            async with websockets.connect(ws_url_1) as ws1:
                # Wait for join notification
                join_msg = await asyncio.wait_for(ws1.recv(), timeout=5.0)
                join_data = json.loads(join_msg)
                
                if join_data.get("type") == "user_joined":
                    self.log_test("WebSocket User Join", True, f"User join notification received")
                    
                    # Connect second user
                    async with websockets.connect(ws_url_2) as ws2:
                        # First user should receive notification about second user joining
                        try:
                            second_join_msg = await asyncio.wait_for(ws1.recv(), timeout=5.0)
                            second_join_data = json.loads(second_join_msg)
                            
                            if second_join_data.get("type") == "user_joined" and second_join_data.get("username") == username_2:
                                self.log_test("WebSocket Multi-User Join", True, "Multi-user join notifications working")
                                return True
                            else:
                                self.log_test("WebSocket Multi-User Join", False, f"Unexpected notification: {second_join_data}")
                                return False
                                
                        except asyncio.TimeoutError:
                            self.log_test("WebSocket Multi-User Join", False, "Timeout waiting for second user join notification")
                            return False
                else:
                    self.log_test("WebSocket User Join", False, f"Expected user_joined, got: {join_data}")
                    return False
                    
        except Exception as e:
            self.log_test("WebSocket User Notifications", False, f"Error: {str(e)}")
            return False

    async def run_websocket_tests(self, room_id):
        """Run all WebSocket tests"""
        print("\n🔌 Testing WebSocket functionality...")
        
        # Test basic connection and messaging
        await self.test_websocket_connection(room_id)
        
        # Test user notifications
        await self.test_websocket_user_notifications(room_id)

    def run_api_tests(self):
        """Run all REST API tests"""
        print("🌐 Testing REST API endpoints...")
        
        # Test root endpoint
        self.test_root_endpoint()
        
        # Initialize default rooms
        self.test_init_default_rooms()
        
        # Get rooms list
        rooms = self.test_get_rooms()
        
        # Test message history for first room if available
        if rooms and len(rooms) > 0:
            first_room_id = rooms[0]['id']
            self.test_get_room_messages(first_room_id)
            return first_room_id
        
        # Test custom room creation
        custom_room = self.test_create_custom_room()
        if custom_room:
            return custom_room['id']
            
        return None

    def print_summary(self):
        """Print test summary"""
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result['success'])
        failed_tests = total_tests - passed_tests
        
        print(f"\n📊 TEST SUMMARY")
        print(f"{'='*50}")
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests} ✅")
        print(f"Failed: {failed_tests} ❌")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            print(f"\n❌ FAILED TESTS:")
            for result in self.test_results:
                if not result['success']:
                    print(f"  - {result['test']}: {result['message']}")
        
        return failed_tests == 0

async def main():
    """Main test runner"""
    print("🚀 Starting Lofi Chatroom Backend Tests")
    print("="*50)
    
    tester = BackendTester()
    
    # Run API tests first
    room_id = tester.run_api_tests()
    
    # Run WebSocket tests if we have a room
    if room_id:
        await tester.run_websocket_tests(room_id)
    else:
        print("⚠️  Skipping WebSocket tests - no room available")
    
    # Print summary
    all_passed = tester.print_summary()
    
    return all_passed

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)