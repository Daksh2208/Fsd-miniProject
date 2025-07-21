from fastapi import FastAPI, WebSocket, HTTPException, Depends, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
import json
import asyncio
from datetime import datetime
import os
from dotenv import load_dotenv
from bson import ObjectId
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

app = FastAPI(title="MindMaze API", version="1.0.0")

# CORS - Updated to include Vite's default port
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8080",
        "http://localhost:5174",  # Add this if your new frontend runs here
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database
MONGODB_URL = os.getenv("MONGODB_URL")
if not MONGODB_URL:
    raise ValueError("MONGODB_URL environment variable is not set")

client = AsyncIOMotorClient(MONGODB_URL)
db = client.mindmaze

# Helper function to serialize MongoDB documents
def serialize_mongo_doc(doc):
    """Convert MongoDB document to JSON serializable format"""
    if doc is None:
        return None
    
    if isinstance(doc, list):
        return [serialize_mongo_doc(item) for item in doc]
    
    if isinstance(doc, dict):
        serialized = {}
        for key, value in doc.items():
            if isinstance(value, ObjectId):
                serialized[key] = str(value)
            elif isinstance(value, dict):
                serialized[key] = serialize_mongo_doc(value)
            elif isinstance(value, list):
                serialized[key] = [serialize_mongo_doc(item) for item in value]
            else:
                serialized[key] = value
        return serialized
    
    return doc

# Models
class User(BaseModel):
    username: str
    score: int = 0
    password: str = Field(default="", exclude=True)  # Accept but ignore
    confirmPassword: str = Field(default="", exclude=True)  # Accept but ignore
    email: str = Field(default="", exclude=True)  # Accept but ignore

class GameSession(BaseModel):
    players: List[str]
    current_puzzle: str
    answers: Dict[str, str] = {}
    winner: Optional[str] = None

class WebSocketMessage(BaseModel):
    type: str
    message: Optional[str] = None
    answer: Optional[str] = None

# In-memory storage for active games
active_games: Dict[str, GameSession] = {}
connected_players: Dict[str, WebSocket] = {}

# Simple puzzles
PUZZLES = [
    {"question": "What is 2 + 2?", "answer": "4"},
    {"question": "What color do you get when you mix red and blue?", "answer": "purple"},
    {"question": "What is the capital of France?", "answer": "paris"},
    {"question": "How many sides does a triangle have?", "answer": "3"},
    {"question": "What is 5 x 3?", "answer": "15"},
    {"question": "What is the largest planet in our solar system?", "answer": "jupiter"},
    {"question": "How many minutes are in an hour?", "answer": "60"},
    {"question": "What is 10 - 7?", "answer": "3"},
    {"question": "What is the square root of 16?", "answer": "4"},
    {"question": "What animal says 'moo'?", "answer": "cow"}
]

# Test database connection on startup
@app.on_event("startup")
async def startup_event():
    try:
        # Test the connection
        await client.admin.command('ping')
        logger.info("✅ Connected to MongoDB Atlas successfully!")
        
        # Create indexes for better performance
        try:
            await db.users.create_index("username", unique=True)
            logger.info("✅ Database indexes created")
        except Exception as e:
            logger.warning(f"Index creation warning: {e}")
        
    except Exception as e:
        logger.error(f"❌ Failed to connect to MongoDB Atlas: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    client.close()
    logger.info("✅ MongoDB connection closed")

# Routes
@app.get("/")
async def root():
    return {"message": "MindMaze API is running!", "status": "connected"}

@app.post("/api/register")
async def register(user: User):
    try:
        existing_user = await db.users.find_one({"username": user.username})
        if existing_user:
            raise HTTPException(status_code=400, detail="Username already exists")
        
        user_dict = user.dict()
        user_dict.pop("password", None)
        user_dict.pop("confirmPassword", None)
        user_dict.pop("email", None)
        user_dict["created_at"] = datetime.utcnow()
        await db.users.insert_one(user_dict)
        return {"message": "User created successfully", "user": serialize_mongo_doc(user_dict)}
    except HTTPException:
        raise
    except Exception as e:
        if "duplicate key" in str(e):
            raise HTTPException(status_code=400, detail="Username already exists")
        logger.error(f"Registration error: {e}")
        raise HTTPException(status_code=500, detail="Database error")

@app.post("/api/signup")
async def signup(user: User):
    # Reuse the register logic
    try:
        existing_user = await db.users.find_one({"username": user.username})
        if existing_user:
            raise HTTPException(status_code=400, detail="Username already exists")
        
        user_dict = user.dict()
        user_dict.pop("password", None)
        user_dict.pop("confirmPassword", None)
        user_dict.pop("email", None)
        user_dict["created_at"] = datetime.utcnow()
        await db.users.insert_one(user_dict)
        return {"message": "User created successfully", "user": serialize_mongo_doc(user_dict)}
    except HTTPException:
        raise
    except Exception as e:
        if "duplicate key" in str(e):
            raise HTTPException(status_code=400, detail="Username already exists")
        logger.error(f"Signup error: {e}")
        raise HTTPException(status_code=500, detail="Database error")

@app.post("/api/login")
async def login(user: User):
    try:
        logger.info(f"Login attempt for user: {user.username}")
        existing_user = await db.users.find_one({"username": user.username})
        if not existing_user:
            logger.warning(f"Login failed: user {user.username} not found")
            raise HTTPException(status_code=400, detail="User not found")
        
        # Update last login
        await db.users.update_one(
            {"username": user.username},
            {"$set": {"last_login": datetime.utcnow()}}
        )
        
        # Serialize the user document to handle ObjectId
        serialized_user = serialize_mongo_doc(existing_user)
        return {"message": "Login successful", "user": serialized_user}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(status_code=500, detail="Database error")

@app.get("/api/leaderboard")
async def get_leaderboard():
    try:
        users = await db.users.find(
            {}, 
            {"_id": 0, "username": 1, "score": 1}
        ).sort("score", -1).limit(10).to_list(10)
        return users
    except Exception as e:
        logger.error(f"Leaderboard error: {e}")
        raise HTTPException(status_code=500, detail="Database error")

@app.get("/api/puzzles")
async def get_puzzles():
    return {"puzzles": PUZZLES}

@app.get("/api/stats")
async def get_stats():
    try:
        total_users = await db.users.count_documents({})
        return {
            "total_users": total_users,
            "active_games": len(active_games),
            "connected_players": len(connected_players)
        }
    except Exception as e:
        logger.error(f"Stats error: {e}")
        raise HTTPException(status_code=500, detail="Database error")

# WebSocket for real-time game
@app.websocket("/ws/{username}")
async def websocket_endpoint(websocket: WebSocket, username: str):
    await websocket.accept()
    connected_players[username] = websocket
    logger.info(f"✅ WebSocket connected for user: {username}")
    
    try:
        # Send welcome message
        await websocket.send_text(json.dumps({
            "type": "connected",
            "message": f"Welcome {username}!",
            "timestamp": datetime.utcnow().isoformat()
        }))
        
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                
                if message["type"] == "find_match":
                    await handle_matchmaking(username, websocket)
                elif message["type"] == "submit_answer":
                    await handle_answer(username, message.get("answer", ""), websocket)
                else:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": "Unknown message type"
                    }))
                    
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "Invalid JSON format"
                }))
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for user: {username}")
    except Exception as e:
        logger.error(f"WebSocket error for {username}: {e}")
    finally:
        await cleanup_player(username)

async def cleanup_player(username: str):
    """Clean up player data when they disconnect"""
    if username in connected_players:
        del connected_players[username]
        
    # Remove player from any active games
    for game_id, game in list(active_games.items()):
        if username in game.players:
            del active_games[game_id]
            # Notify other players
            for player in game.players:
                if player != username and player in connected_players:
                    try:
                        await connected_players[player].send_text(json.dumps({
                            "type": "opponent_disconnected",
                            "message": "Your opponent disconnected"
                        }))
                    except Exception as e:
                        logger.error(f"Error notifying player {player}: {e}")

async def handle_matchmaking(username: str, websocket: WebSocket):
    """Handle matchmaking logic"""
    # Find existing game waiting for player
    for game_id, game in active_games.items():
        if len(game.players) == 1 and username not in game.players:
            game.players.append(username)
            
            # Start game
            import random
            puzzle = random.choice(PUZZLES)
            game.current_puzzle = puzzle["question"]
            
            # Notify both players
            for player in game.players:
                if player in connected_players:
                    try:
                        await connected_players[player].send_text(json.dumps({
                            "type": "game_start",
                            "game_id": game_id,
                            "puzzle": puzzle["question"],
                            "opponent": [p for p in game.players if p != player][0]
                        }))
                    except Exception as e:
                        logger.error(f"Error starting game for {player}: {e}")
            return
    
    # Create new game
    game_id = f"game_{len(active_games) + 1}_{username}"
    active_games[game_id] = GameSession(
        players=[username],
        current_puzzle=""
    )
    
    await websocket.send_text(json.dumps({
        "type": "waiting_for_opponent",
        "game_id": game_id
    }))

async def handle_answer(username: str, answer: str, websocket: WebSocket):
    """Handle answer submission"""
    # Find user's game
    user_game = None
    game_id = None
    
    for gid, game in active_games.items():
        if username in game.players:
            user_game = game
            game_id = gid
            break
    
    if not user_game:
        await websocket.send_text(json.dumps({
            "type": "error",
            "message": "No active game found"
        }))
        return
    
    # Check answer
    correct_answer = None
    for puzzle in PUZZLES:
        if puzzle["question"] == user_game.current_puzzle:
            correct_answer = puzzle["answer"]
            break
    
    if answer.lower().strip() == correct_answer.lower():
        user_game.winner = username
        
        # Update score in database
        try:
            await db.users.update_one(
                {"username": username},
                {"$inc": {"score": 10}}
            )
        except Exception as e:
            logger.error(f"Error updating score: {e}")
        
        # Notify both players
        for player in user_game.players:
            if player in connected_players:
                is_winner = player == username
                try:
                    await connected_players[player].send_text(json.dumps({
                        "type": "game_end",
                        "winner": username,
                        "correct_answer": correct_answer,
                        "is_winner": is_winner,
                        "message": "You won! +10 points" if is_winner else f"{username} won!"
                    }))
                except Exception as e:
                    logger.error(f"Error sending game end message to {player}: {e}")
        
        # Clean up game
        del active_games[game_id]
    else:
        await websocket.send_text(json.dumps({
            "type": "wrong_answer",
            "message": "Wrong answer! Try again."
        }))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)