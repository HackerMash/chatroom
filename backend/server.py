from fastapi import FastAPI, APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Dict, Set
import uuid
from datetime import datetime
import json

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# WebSocket Connection Manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.user_rooms: Dict[str, str] = {}  # user_id -> room_id
        self.room_users: Dict[str, Set[str]] = {}  # room_id -> set of user_ids

    async def connect(self, websocket: WebSocket, user_id: str, username: str, room_id: str):
        await websocket.accept()
        self.active_connections[user_id] = websocket
        self.user_rooms[user_id] = room_id
        
        if room_id not in self.room_users:
            self.room_users[room_id] = set()
        self.room_users[room_id].add(user_id)
        
        # Notify room about new user
        await self.broadcast_to_room(room_id, {
            "type": "user_joined",
            "user_id": user_id,
            "username": username,
            "timestamp": datetime.utcnow().isoformat(),
            "user_count": len(self.room_users[room_id])
        })

    def disconnect(self, user_id: str):
        if user_id in self.active_connections:
            del self.active_connections[user_id]
        
        if user_id in self.user_rooms:
            room_id = self.user_rooms[user_id]
            del self.user_rooms[user_id]
            
            if room_id in self.room_users:
                self.room_users[room_id].discard(user_id)
                if len(self.room_users[room_id]) == 0:
                    del self.room_users[room_id]

    async def send_personal_message(self, message: dict, user_id: str):
        if user_id in self.active_connections:
            websocket = self.active_connections[user_id]
            await websocket.send_text(json.dumps(message))

    async def broadcast_to_room(self, room_id: str, message: dict):
        if room_id in self.room_users:
            for user_id in list(self.room_users[room_id]):
                await self.send_personal_message(message, user_id)

    def get_room_user_count(self, room_id: str) -> int:
        return len(self.room_users.get(room_id, set()))

manager = ConnectionManager()

# Define Models
class ChatMessage(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    username: str
    room_id: str
    message: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    message_type: str = "chat"  # chat, system

class ChatMessageCreate(BaseModel):
    user_id: str
    username: str
    room_id: str
    message: str
    message_type: str = "chat"

class Room(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    niche: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    user_count: int = 0

class RoomCreate(BaseModel):
    name: str
    description: str
    niche: str

# WebSocket endpoint
@app.websocket("/ws/{room_id}/{user_id}/{username}")
async def websocket_endpoint(websocket: WebSocket, room_id: str, user_id: str, username: str):
    await manager.connect(websocket, user_id, username, room_id)
    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            # Create message in database
            chat_message = ChatMessage(
                user_id=user_id,
                username=username,
                room_id=room_id,
                message=message_data["message"],
                message_type="chat"
            )
            
            # Store in database
            await db.chat_messages.insert_one(chat_message.dict())
            
            # Broadcast to room
            await manager.broadcast_to_room(room_id, {
                "type": "message",
                "id": chat_message.id,
                "user_id": user_id,
                "username": username,
                "message": message_data["message"],
                "timestamp": chat_message.timestamp.isoformat(),
                "user_count": manager.get_room_user_count(room_id)
            })
            
    except WebSocketDisconnect:
        manager.disconnect(user_id)
        await manager.broadcast_to_room(room_id, {
            "type": "user_left",
            "user_id": user_id,
            "username": username,
            "timestamp": datetime.utcnow().isoformat(),
            "user_count": manager.get_room_user_count(room_id)
        })

# REST API endpoints
@api_router.get("/")
async def root():
    return {"message": "Lofi Chatroom API"}

@api_router.post("/rooms", response_model=Room)
async def create_room(room: RoomCreate):
    room_obj = Room(**room.dict())
    await db.rooms.insert_one(room_obj.dict())
    return room_obj

@api_router.get("/rooms", response_model=List[Room])
async def get_rooms():
    rooms = await db.rooms.find().to_list(100)
    room_list = []
    for room in rooms:
        room_obj = Room(**room)
        room_obj.user_count = manager.get_room_user_count(room_obj.id)
        room_list.append(room_obj)
    return room_list

@api_router.get("/rooms/{room_id}/messages")
async def get_room_messages(room_id: str, limit: int = 50):
    messages = await db.chat_messages.find(
        {"room_id": room_id}
    ).sort("timestamp", -1).limit(limit).to_list(limit)
    
    return sorted([ChatMessage(**msg) for msg in messages], key=lambda x: x.timestamp)

# Create default rooms
@api_router.post("/init-default-rooms")
async def init_default_rooms():
    default_rooms = [
        {
            "name": "🎵 General Lofi",
            "description": "General chat while listening to chill beats",
            "niche": "general"
        },
        {
            "name": "💻 Study & Work",
            "description": "Focus together while studying or working",
            "niche": "productivity"
        },
        {
            "name": "🎨 Creative Minds",
            "description": "For artists, writers, and creative souls",
            "niche": "creative"
        },
        {
            "name": "🌙 Late Night Vibes",
            "description": "Night owls and insomniacs welcome",
            "niche": "nightowls"
        }
    ]
    
    for room_data in default_rooms:
        existing = await db.rooms.find_one({"name": room_data["name"]})
        if not existing:
            room = Room(**room_data)
            await db.rooms.insert_one(room.dict())
    
    return {"message": "Default rooms initialized"}

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()