import React, { useState, useEffect, useRef } from 'react';
import './App.css';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;
const WS_URL = BACKEND_URL.replace('https://', 'wss://').replace('http://', 'ws://');

// Lofi music tracks (royalty-free)
const LOFI_TRACKS = [
  {
    name: "Chill Beats 1",
    url: "https://www.soundjay.com/misc/sounds-1042.wav" // Sample - replace with actual lofi
  }
];

function App() {
  // Chat state
  const [rooms, setRooms] = useState([]);
  const [currentRoom, setCurrentRoom] = useState(null);
  const [messages, setMessages] = useState([]);
  const [newMessage, setNewMessage] = useState('');
  const [username, setUsername] = useState('');
  const [userId] = useState(() => 'user_' + Math.random().toString(36).substr(2, 9));
  const [isConnected, setIsConnected] = useState(false);
  const [userCount, setUserCount] = useState(0);
  
  // Music state
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTrack, setCurrentTrack] = useState(0);
  const [volume, setVolume] = useState(0.3);
  
  // Refs
  const ws = useRef(null);
  const audioRef = useRef(null);
  const messagesEndRef = useRef(null);

  // Initialize default rooms
  useEffect(() => {
    initializeRooms();
    fetchRooms();
  }, []);

  // Auto-scroll to bottom of messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const initializeRooms = async () => {
    try {
      await fetch(`${API}/init-default-rooms`, { method: 'POST' });
    } catch (error) {
      console.error('Error initializing rooms:', error);
    }
  };

  const fetchRooms = async () => {
    try {
      const response = await fetch(`${API}/rooms`);
      const roomData = await response.json();
      setRooms(roomData);
    } catch (error) {
      console.error('Error fetching rooms:', error);
    }
  };

  const connectToRoom = async (room) => {
    if (!username.trim()) {
      alert('Please enter a username first!');
      return;
    }

    // Disconnect from current room
    if (ws.current) {
      ws.current.close();
    }

    setCurrentRoom(room);
    setMessages([]);

    // Fetch recent messages
    try {
      const response = await fetch(`${API}/rooms/${room.id}/messages`);
      const messageData = await response.json();
      setMessages(messageData);
    } catch (error) {
      console.error('Error fetching messages:', error);
    }

    // Connect WebSocket
    const wsUrl = `${WS_URL}/ws/${room.id}/${userId}/${encodeURIComponent(username)}`;
    ws.current = new WebSocket(wsUrl);

    ws.current.onopen = () => {
      setIsConnected(true);
      console.log('Connected to room:', room.name);
    };

    ws.current.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      if (data.type === 'message') {
        setMessages(prev => [...prev, {
          id: data.id,
          user_id: data.user_id,
          username: data.username,
          message: data.message,
          timestamp: data.timestamp,
          message_type: 'chat'
        }]);
        setUserCount(data.user_count);
      } else if (data.type === 'user_joined') {
        setMessages(prev => [...prev, {
          id: 'system_' + Date.now(),
          username: 'System',
          message: `${data.username} joined the room`,
          timestamp: data.timestamp,
          message_type: 'system'
        }]);
        setUserCount(data.user_count);
      } else if (data.type === 'user_left') {
        setMessages(prev => [...prev, {
          id: 'system_' + Date.now(),
          username: 'System',
          message: `${data.username} left the room`,
          timestamp: data.timestamp,
          message_type: 'system'
        }]);
        setUserCount(data.user_count);
      }
    };

    ws.current.onclose = () => {
      setIsConnected(false);
      console.log('Disconnected from room');
    };

    ws.current.onerror = (error) => {
      console.error('WebSocket error:', error);
      setIsConnected(false);
    };
  };

  const sendMessage = (e) => {
    e.preventDefault();
    if (newMessage.trim() && ws.current && ws.current.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify({
        message: newMessage.trim()
      }));
      setNewMessage('');
    }
  };

  const toggleMusic = () => {
    if (audioRef.current) {
      if (isPlaying) {
        audioRef.current.pause();
      } else {
        audioRef.current.play().catch(e => {
          console.log('Autoplay prevented:', e);
        });
      }
      setIsPlaying(!isPlaying);
    }
  };

  const handleVolumeChange = (e) => {
    const newVolume = e.target.value;
    setVolume(newVolume);
    if (audioRef.current) {
      audioRef.current.volume = newVolume;
    }
  };

  const formatTime = (timestamp) => {
    return new Date(timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  if (!username) {
    return (
      <div 
        className="min-h-screen bg-cover bg-center bg-no-repeat flex items-center justify-center"
        style={{
          backgroundImage: `linear-gradient(rgba(0, 0, 0, 0.6), rgba(0, 0, 0, 0.6)), url('https://images.unsplash.com/photo-1677568554453-ae5baf28da6c?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NTY2Njl8MHwxfHNlYXJjaHwxfHxjb3p5JTIwbG9maSUyMHJvb218ZW58MHx8fHwxNzUzMDIxNjE5fDA&ixlib=rb-4.1.0&q=85')`
        }}
      >
        <div className="bg-white/90 backdrop-blur-sm rounded-2xl p-8 shadow-2xl max-w-md w-full mx-4">
          <div className="text-center mb-6">
            <h1 className="text-3xl font-bold text-gray-800 mb-2">🎵 Lofi Chatrooms</h1>
            <p className="text-gray-600">Connect with like-minded people while enjoying chill beats</p>
          </div>
          
          <form onSubmit={(e) => {
            e.preventDefault();
            if (username.trim()) {
              // Username is set, the app will re-render
            }
          }}>
            <div className="mb-4">
              <label className="block text-gray-700 text-sm font-bold mb-2">
                Choose your username
              </label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-blue-500"
                placeholder="Enter your username..."
                maxLength={20}
                required
              />
            </div>
            <button
              type="submit"
              className="w-full bg-gradient-to-r from-purple-500 to-blue-600 text-white font-bold py-2 px-4 rounded-lg hover:from-purple-600 hover:to-blue-700 transition duration-200"
            >
              Enter Chatrooms
            </button>
          </form>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Header */}
      <header className="bg-white shadow-lg border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <div className="flex items-center">
              <h1 className="text-2xl font-bold text-gray-800">🎵 Lofi Chatrooms</h1>
              {currentRoom && (
                <div className="ml-6 text-sm text-gray-600">
                  <span className="font-medium">{currentRoom.name}</span>
                  <span className="ml-2">• {userCount} users online</span>
                </div>
              )}
            </div>
            
            {/* Music Controls */}
            <div className="flex items-center space-x-4">
              <button
                onClick={toggleMusic}
                className="bg-purple-500 hover:bg-purple-600 text-white px-4 py-2 rounded-lg transition duration-200"
              >
                {isPlaying ? '⏸️ Pause Music' : '▶️ Play Lofi'}
              </button>
              <div className="flex items-center space-x-2">
                <span className="text-sm text-gray-600">🔊</span>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.1"
                  value={volume}
                  onChange={handleVolumeChange}
                  className="w-20"
                />
              </div>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Room List Sidebar */}
          <div className="lg:col-span-1">
            <div className="bg-white rounded-lg shadow-lg p-4">
              <h2 className="text-lg font-semibold text-gray-800 mb-4">Rooms</h2>
              <div className="space-y-2">
                {rooms.map((room) => (
                  <button
                    key={room.id}
                    onClick={() => connectToRoom(room)}
                    className={`w-full text-left p-3 rounded-lg transition duration-200 ${
                      currentRoom?.id === room.id
                        ? 'bg-purple-100 border-purple-300 border'
                        : 'hover:bg-gray-50'
                    }`}
                  >
                    <div className="font-medium text-gray-800">{room.name}</div>
                    <div className="text-xs text-gray-500 mt-1">{room.description}</div>
                    <div className="text-xs text-purple-600 mt-1">{room.user_count || 0} users</div>
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Chat Area */}
          <div className="lg:col-span-3">
            {currentRoom ? (
              <div className="bg-white rounded-lg shadow-lg h-96 lg:h-[600px] flex flex-col">
                {/* Messages */}
                <div className="flex-1 overflow-y-auto p-4 space-y-3">
                  {messages.map((message) => (
                    <div
                      key={message.id}
                      className={`flex ${
                        message.message_type === 'system' ? 'justify-center' : 'justify-start'
                      }`}
                    >
                      <div
                        className={`max-w-xs lg:max-w-md px-3 py-2 rounded-lg ${
                          message.message_type === 'system'
                            ? 'bg-gray-200 text-gray-600 text-sm italic'
                            : message.user_id === userId
                            ? 'bg-purple-500 text-white ml-auto'
                            : 'bg-gray-100 text-gray-800'
                        }`}
                      >
                        {message.message_type !== 'system' && message.user_id !== userId && (
                          <div className="text-xs text-purple-600 font-medium mb-1">
                            {message.username}
                          </div>
                        )}
                        <div>{message.message}</div>
                        <div className="text-xs opacity-70 mt-1">
                          {formatTime(message.timestamp)}
                        </div>
                      </div>
                    </div>
                  ))}
                  <div ref={messagesEndRef} />
                </div>

                {/* Message Input */}
                <form onSubmit={sendMessage} className="border-t p-4">
                  <div className="flex space-x-2">
                    <input
                      type="text"
                      value={newMessage}
                      onChange={(e) => setNewMessage(e.target.value)}
                      placeholder="Type your message..."
                      className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-purple-500"
                      disabled={!isConnected}
                    />
                    <button
                      type="submit"
                      disabled={!isConnected || !newMessage.trim()}
                      className="bg-purple-500 hover:bg-purple-600 disabled:bg-gray-300 text-white px-6 py-2 rounded-lg transition duration-200"
                    >
                      Send
                    </button>
                  </div>
                  <div className="mt-2 text-xs text-gray-500">
                    {isConnected ? `Connected as ${username}` : 'Connecting...'}
                  </div>
                </form>
              </div>
            ) : (
              <div className="bg-white rounded-lg shadow-lg h-96 lg:h-[600px] flex items-center justify-center">
                <div className="text-center text-gray-500">
                  <div className="text-4xl mb-4">🎵</div>
                  <h3 className="text-lg font-medium mb-2">Welcome to Lofi Chatrooms</h3>
                  <p>Select a room from the sidebar to start chatting with like-minded people</p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Hidden Audio Element */}
      <audio
        ref={audioRef}
        loop
        onPlay={() => setIsPlaying(true)}
        onPause={() => setIsPlaying(false)}
      >
        <source src="https://www.bensound.com/bensound-music/bensound-creativeminds.mp3" type="audio/mpeg" />
        Your browser does not support the audio element.
      </audio>
    </div>
  );
}

export default App;