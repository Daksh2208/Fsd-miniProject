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
import random

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
    category: str
    current_puzzle: Dict[str, str]
    answers: Dict[str, str] = {}
    winner: Optional[str] = None

class WebSocketMessage(BaseModel):
    type: str
    message: Optional[str] = None
    answer: Optional[str] = None
    category: Optional[str] = None

# In-memory storage for active games
active_games: Dict[str, GameSession] = {}
connected_players: Dict[str, WebSocket] = {}
waiting_players: Dict[str, Dict] = {}  # Store players waiting for matches by category

# Category-specific puzzles
CATEGORY_PUZZLES = {
    "very_basic_math": [
    {"question": "What is 2 + 2?", "answer": "4"},
    {"question": "What is 5 x 3?", "answer": "15"},
    {"question": "What is 10 - 7?", "answer": "3"},
    {"question": "What is 8 ÷ 2?", "answer": "4"},
    {"question": "What is 6 + 4?", "answer": "10"},
    {"question": "What is 9 - 5?", "answer": "4"},
    {"question": "What is 3 x 4?", "answer": "12"},
    {"question": "What is 20 ÷ 4?", "answer": "5"},
    {"question": "What is 7 + 8?", "answer": "15"},
    {"question": "What is 12 - 3?", "answer": "9"},
    {"question": "What is 4 + 5?", "answer": "9"},
    {"question": "What is 6 x 2?", "answer": "12"},
    {"question": "What is 15 - 6?", "answer": "9"},
    {"question": "What is 12 ÷ 3?", "answer": "4"},
    {"question": "What is 3 + 7?", "answer": "10"},
    {"question": "What is 8 - 4?", "answer": "4"},
    {"question": "What is 5 x 5?", "answer": "25"},
    {"question": "What is 18 ÷ 3?", "answer": "6"},
    {"question": "What is 9 + 3?", "answer": "12"},
    {"question": "What is 11 - 5?", "answer": "6"},
    {"question": "What is 4 x 6?", "answer": "24"},
    {"question": "What is 16 ÷ 4?", "answer": "4"},
    {"question": "What is 5 + 6?", "answer": "11"},
    {"question": "What is 14 - 8?", "answer": "6"},
    {"question": "What is 7 x 3?", "answer": "21"},
    {"question": "What is 24 ÷ 6?", "answer": "4"},
    {"question": "What is 8 + 7?", "answer": "15"},
    {"question": "What is 13 - 4?", "answer": "9"},
    {"question": "What is 6 x 3?", "answer": "18"},
    {"question": "What is 10 ÷ 2?", "answer": "5"},
    {"question": "What is 4 + 8?", "answer": "12"},
    {"question": "What is 9 - 2?", "answer": "7"},
    {"question": "What is 5 x 4?", "answer": "20"},
    {"question": "What is 15 ÷ 3?", "answer": "5"},
    {"question": "What is 6 + 9?", "answer": "15"},
    {"question": "What is 11 - 7?", "answer": "4"},
    {"question": "What is 8 x 2?", "answer": "16"},
    {"question": "What is 21 ÷ 7?", "answer": "3"},
    {"question": "What is 3 + 9?", "answer": "12"},
    {"question": "What is 10 - 8?", "answer": "2"},
    {"question": "What is 4 x 4?", "answer": "16"},
    {"question": "What is 18 ÷ 2?", "answer": "9"},
    {"question": "What is 7 + 5?", "answer": "12"},
    {"question": "What is 14 - 9?", "answer": "5"},
    {"question": "What is 3 x 5?", "answer": "15"},
    {"question": "What is 12 ÷ 4?", "answer": "3"},
    {"question": "What is 8 + 6?", "answer": "14"},
    {"question": "What is 16 - 7?", "answer": "9"},
    {"question": "What is 6 x 5?", "answer": "30"},
    {"question": "What is 20 ÷ 5?", "answer": "4"}
],


    
    "Oral_math": [
    {"question": "What is the square of 17?", "answer": "289"},
    {"question": "What is 15% of 240?", "answer": "36"},
    {"question": "If 3x = 45, what is x?", "answer": "15"},
    {"question": "What is the value of 2⁵ + 2³?", "answer": "40"},
    {"question": "What is the cube root of 64?", "answer": "4"},
    {"question": "What is 1/3 of 180?", "answer": "60"},
    {"question": "What is the next prime number after 29?", "answer": "31"},
    {"question": "What is (6² - 4²)?", "answer": "20"},
    {"question": "If x = 5, what is the value of x² - 3x + 4?", "answer": "14"},
    {"question": "What is the remainder when 103 is divided by 9?", "answer": "4"},
    {"question": "What is the square of 23?", "answer": "529"},
    {"question": "What is 35% of 320?", "answer": "112"},
    {"question": "If 7x = 133, what is x?", "answer": "19"},
    {"question": "What is the value of 3⁴ - 2⁴?", "answer": "65"},
    {"question": "What is the cube root of 729?", "answer": "9"},
    {"question": "What is 5/8 of 480?", "answer": "300"},
    {"question": "What is the next prime number after 97?", "answer": "101"},
    {"question": "What is (11² - 7²)?", "answer": "72"},
    {"question": "If x = 9, what is the value of 2x² - 5x + 3?", "answer": "120"},
    {"question": "What is the remainder when 257 is divided by 11?", "answer": "4"},
    {"question": "What is the square of 26?", "answer": "676"},
    {"question": "What is 45% of 260?", "answer": "117"},
    {"question": "If 9x = 198, what is x?", "answer": "22"},
    {"question": "What is the value of 4⁴ - 3⁴?", "answer": "175"},
    {"question": "What is the cube root of 1000?", "answer": "10"},
    {"question": "What is 3/7 of 420?", "answer": "180"},
    {"question": "What is the next prime number after 113?", "answer": "127"},
    {"question": "What is (12² - 8²)?", "answer": "80"},
    {"question": "If x = 7, what is the value of 3x² - 4x + 5?", "answer": "124"},
    {"question": "What is the remainder when 341 is divided by 12?", "answer": "5"},
    {"question": "What is the square of 21?", "answer": "441"},
    {"question": "What is 22% of 450?", "answer": "99"},
    {"question": "If 5x = 115, what is x?", "answer": "23"},
    {"question": "What is the value of 2⁶ + 3³?", "answer": "91"},
    {"question": "What is the cube root of 1728?", "answer": "12"},
    {"question": "What is 2/9 of 630?", "answer": "140"},
    {"question": "What is the next prime number after 139?", "answer": "149"},
    {"question": "What is (15² - 9²)?", "answer": "144"},
    {"question": "If x = 10, what is the value of x² - 6x + 8?", "answer": "48"},
    {"question": "What is the remainder when 289 is divided by 13?", "answer": "3"},
    {"question": "What is the square of 24?", "answer": "576"},
    {"question": "What is 18% of 500?", "answer": "90"},
    {"question": "If 8x = 184, what is x?", "answer": "23"},
    {"question": "What is the value of 5³ + 4²?", "answer": "141"},
    {"question": "What is the cube root of 3375?", "answer": "15"},
    {"question": "What is 4/5 of 375?", "answer": "300"},
    {"question": "What is the next prime number after 167?", "answer": "173"},
    {"question": "What is (13² - 6²)?", "answer": "133"},
    {"question": "If x = 11, what is the value of 2x² - 7x + 6?", "answer": "109"},
    {"question": "What is the remainder when 412 is divided by 15?", "answer": "7"},
    {"question": "What is the square of 29?", "answer": "841"},
    {"question": "What is 33% of 360?", "answer": "118.8"},
    {"question": "If 6x = 162, what is x?", "answer": "27"},
    {"question": "What is the value of 7³ - 5³?", "answer": "218"},
    {"question": "What is the cube root of 2197?", "answer": "13"},
    {"question": "What is 5/6 of 240?", "answer": "200"},
    {"question": "What is the next prime number after 191?", "answer": "193"},
    {"question": "What is (14² - 10²)?", "answer": "96"},
    {"question": "If x = 12, what is the value of 3x² - 8x + 7?", "answer": "391"},
    {"question": "What is the remainder when 378 is divided by 17?", "answer": "3"}
],



   "social_science": [
    {"question": "What is the capital of France?", "answer": "paris"},
    {"question": "Who was the first President of the United States?", "answer": "george washington"},
    {"question": "In which year did World War II end?", "answer": "1945"},
    {"question": "What is the largest country by area?", "answer": "russia"},
    {"question": "Which river is the longest in the world?", "answer": "nile"},
    {"question": "What is the capital of Japan?", "answer": "tokyo"},
    {"question": "Who wrote 'Romeo and Juliet'?", "answer": "shakespeare"},
    {"question": "Which continent is Egypt in?", "answer": "africa"},
    {"question": "What year did the Berlin Wall fall?", "answer": "1989"},
    {"question": "What is the smallest country in the world?", "answer": "vatican city"},
    {"question": "What is the capital of Brazil?", "answer": "brasilia"},
    {"question": "Who was the first woman to win a Nobel Prize?", "answer": "marie curie"},
    {"question": "In which year did the American Civil War begin?", "answer": "1861"},
    {"question": "What is the largest desert in the world?", "answer": "sahara"},
    {"question": "Which country has the most population in 2025?", "answer": "india"},
    {"question": "What is the capital of Australia?", "answer": "canberra"},
    {"question": "Who wrote 'Pride and Prejudice'?", "answer": "jane austen"},
    {"question": "Which continent is home to the Amazon Rainforest?", "answer": "south america"},
    {"question": "In which year did Nelson Mandela become president of South Africa?", "answer": "1994"},
    {"question": "What is the longest mountain range in the world?", "answer": "andes"},
    {"question": "What is the capital of Canada?", "answer": "ottawa"},
    {"question": "Who was the leader of the Soviet Union during World War II?", "answer": "joseph stalin"},
    {"question": "Which ocean is the largest?", "answer": "pacific"},
    {"question": "What year did the European Union officially form?", "answer": "1993"},
    {"question": "What is the capital of South Africa?", "answer": "pretoria"},
    {"question": "Who wrote '1984'?", "answer": "george orwell"},
    {"question": "Which country was the first to grant women the right to vote?", "answer": "new zealand"},
    {"question": "What is the capital of India?", "answer": "new delhi"},
    {"question": "In which year did the French Revolution begin?", "answer": "1789"},
    {"question": "What is the deepest point in the ocean?", "answer": "mariana trench"},
    {"question": "What is the capital of Germany?", "answer": "berlin"},
    {"question": "Who led the Indian independence movement against British rule?", "answer": "mahatma gandhi"},
    {"question": "In which year did the Titanic sink?", "answer": "1912"},
    {"question": "What is the largest island in the world?", "answer": "greenland"},
    {"question": "Who wrote 'The Odyssey'?", "answer": "homer"},
    {"question": "Which continent has the most countries?", "answer": "africa"},
    {"question": "What year did the United Nations form?", "answer": "1945"},
    {"question": "What is the capital of China?", "answer": "beijing"},
    {"question": "Which river runs through Baghdad?", "answer": "tigris"},
    {"question": "In which year did Christopher Columbus first reach the Americas?", "answer": "1492"}
],


"general_knowledge": [
    {"question": "How many sides does a triangle have?", "answer": "3"},
    {"question": "What is the largest planet in our solar system?", "answer": "jupiter"},
    {"question": "How many minutes are in an hour?", "answer": "60"},
    {"question": "What animal says 'moo'?", "answer": "cow"},
    {"question": "How many days are in a leap year?", "answer": "366"},
    {"question": "What gas do plants absorb from the atmosphere?", "answer": "carbon dioxide"},
    {"question": "How many continents are there?", "answer": "7"},
    {"question": "What is the hardest natural substance?", "answer": "diamond"},
    {"question": "How many bones are in an adult human body?", "answer": "206"},
    {"question": "What is the largest mammal?", "answer": "blue whale"},
    {"question": "What is the chemical symbol for water?", "answer": "h2o"},
    {"question": "How many legs does a spider typically have?", "answer": "8"},
    {"question": "What is the smallest unit of life?", "answer": "cell"},
    {"question": "How many months have 28 days?", "answer": "12"},
    {"question": "What is the closest star to Earth?", "answer": "sun"},
    {"question": "What animal is known as man's best friend?", "answer": "dog"},
    {"question": "How many planets are in our solar system?", "answer": "8"},
    {"question": "What is the primary source of Earth's energy?", "answer": "sun"},
    {"question": "What is the freezing point of water in Celsius?", "answer": "0"},
    {"question": "What is the tallest land animal?", "answer": "giraffe"},
    {"question": "How many sides does a hexagon have?", "answer": "6"},
    {"question": "What gas makes up most of Earth's atmosphere?", "answer": "nitrogen"},
    {"question": "What is the largest organ in the human body?", "answer": "skin"},
    {"question": "How many hours are in a day?", "answer": "24"},
    {"question": "What animal is the fastest land mammal?", "answer": "cheetah"},
    {"question": "What is the chemical symbol for gold?", "answer": "au"},
    {"question": "How many colors are in a rainbow?", "answer": "7"},
    {"question": "What is the smallest planet in our solar system?", "answer": "mercury"},
    {"question": "What is the primary language of Brazil?", "answer": "portuguese"},
    {"question": "How many teeth does an adult human typically have?", "answer": "32"},
    {"question": "What is the boiling point of water in Celsius?", "answer": "100"},
    {"question": "What animal is known for its black and white stripes?", "answer": "zebra"},
    {"question": "How many sides does a cube have?", "answer": "6"},
    {"question": "What is the main source of oxygen in Earth's atmosphere?", "answer": "photosynthesis"},
    {"question": "What is the largest bird in the world?", "answer": "ostrich"},
    {"question": "How many days are in a standard year?", "answer": "365"},
    {"question": "What is the chemical symbol for iron?", "answer": "fe"},
    {"question": "What is the smallest bone in the human body?", "answer": "stapes"},
    {"question": "What animal is known for its long neck and spots?", "answer": "giraffe"},
    {"question": "How many seconds are in a minute?", "answer": "60"}
],





    "riddles": [
       
    {"question": "What has keys but no locks, space but no room?", "answer": "keyboard"},
    {"question": "What gets wet while drying?", "answer": "towel"},
    {"question": "What has hands but cannot clap?", "answer": "clock"},
    {"question": "What goes up but never comes down?", "answer": "age"},
    {"question": "What has a head, a tail, but no body?", "answer": "coin"},
    {"question": "What can travel around the world while staying in a corner?", "answer": "stamp"},
    {"question": "What has many teeth but cannot bite?", "answer": "comb"},
    {"question": "What breaks but never falls?", "answer": "dawn"},
    {"question": "What falls but never breaks?", "answer": "night"},
    {"question": "What is full of holes but still holds water?", "answer": "sponge"},
    {"question": "What has a neck but no head, a body but no legs?", "answer": "shirt"},
    {"question": "What runs all around a house but never moves?", "answer": "fence"},
    {"question": "What can you catch but not throw?", "answer": "cold"},
    {"question": "What has words but never speaks?", "answer": "book"},
    {"question": "What is always running but never moves?", "answer": "refrigerator"},
    {"question": "What has a heart that doesn’t beat?", "answer": "artichoke"},
    {"question": "What is light as a feather but even the strongest cannot hold it for long?", "answer": "breath"},
    {"question": "What gets sharper the more you use it?", "answer": "brain"},
    {"question": "What has roots as deep as a tree but never grows?", "answer": "bank"},
    {"question": "What can fly without wings and cry without eyes?", "answer": "cloud"},
    {"question": "What has one eye but cannot see?", "answer": "needle"},
    {"question": "What is always in front of you but cannot be seen?", "answer": "future"},
    {"question": "What has cities but no houses, forests but no trees?", "answer": "map"},
    {"question": "What can be broken but never held?", "answer": "promise"},
    {"question": "What has a thumb and four fingers but is not alive?", "answer": "glove"},
    {"question": "What is tall when young and short when old?", "answer": "candle"},
    {"question": "What goes through cities and fields but never moves?", "answer": "road"},
    {"question": "What has a mouth but cannot eat?", "answer": "river"},
    {"question": "What is black when you buy it, red when you use it, and gray when you throw it away?", "answer": "charcoal"},
    {"question": "What can you keep after giving it to someone?", "answer": "smile"},
    {"question": "What has legs but cannot walk?", "answer": "table"},
    {"question": "What is so fragile that saying its name breaks it?", "answer": "silence"},
    {"question": "What has a bottom at the top?", "answer": "leg"},
    {"question": "What can fill a room but takes up no space?", "answer": "light"},
    {"question": "What has keys but cannot play music?", "answer": "typewriter"},
    {"question": "What speaks without a mouth and hears without ears?", "answer": "echo"},
    {"question": "What comes once in a minute, twice in a moment, but never in a thousand years?", "answer": "m"},
    {"question": "What has a head but no brain, a body but no soul?", "answer": "coin"},
    {"question": "What is always old but never new?", "answer": "history"},
    {"question": "What can run but never walks, has a mouth but never talks?", "answer": "river"},
    {"question": "What is taken before you can get it?", "answer": "photograph"},
    {"question": "What has wings but cannot fly?", "answer": "penguin"},
    {"question": "What is easy to get into but hard to get out of?", "answer": "trouble"},
    {"question": "What has a lid but no contents?", "answer": "eye"},
    {"question": "What is always coming but never arrives?", "answer": "tomorrow"},
    {"question": "What can you break with just one word?", "answer": "heart"},
    {"question": "What has a spine but no bones?", "answer": "book"},
    {"question": "What gets bigger the more you take away from it?", "answer": "hole"},
    {"question": "What has feet but no toes?", "answer": "ruler"},
    {"question": "What can you make that no one can see, not even you?", "answer": "noise"},
    {"question": "What has branches but no leaves?", "answer": "bank"},
    {"question": "What is alive but drinks no water?", "answer": "fire"},
    {"question": "What can be touched but not seen?", "answer": "air"},
    {"question": "What has a face but no eyes, nose, or mouth?", "answer": "clock"},
    {"question": "What is heavy forward but not backward?", "answer": "ton"},
    {"question": "What has a tongue but cannot taste?", "answer": "shoe"},
    {"question": "What is full all day but empty at night?", "answer": "shoe"},
    {"question": "What can you hold in your hand but never touch?", "answer": "dream"},
    {"question": "What has a roof but no walls?", "answer": "mushroom"},
    {"question": "What can you hear but not see, and it follows you everywhere?", "answer": "voice"},
    {"question": "I am weightless, but you can see me. Put me in a bucket, and I'll make it lighter. What am I?", "answer": "hole"},
    {"question": "I am taken from a mine and shut up in a wooden case, from which I am never released, and yet I am used by almost every person. What am I?", "answer": "pencil"},
    {"question": "I speak without a mouth and hear without ears. I have no body, but I come alive with the wind. What am I?", "answer": "echo"},
    {"question": "I am always hungry and will die if not fed, but whatever I touch will soon turn red. What am I?", "answer": "fire"},
    {"question": "I have branches, but no fruit, trunk, or leaves. I am not a tree, but people come to me for money. What am I?", "answer": "bank"},
    {"question": "I am full of holes, yet I can hold water. You can squeeze me, but you cannot hug me. What am I?", "answer": "sponge"},
    {"question": "I am tall when I am young, but I get shorter as I grow old. I am used to bring light to the dark. What am I?", "answer": "candle"},
    {"question": "I can fly without wings, I can cry without eyes. Whenever I go, darkness flies. What am I?", "answer": "cloud"},
    {"question": "I have a neck but no head, a body but no legs, and arms but no hands. What am I?", "answer": "shirt"},
    {"question": "I am always running, but I never move. I am found in a kitchen, keeping things cool. What am I?", "answer": "refrigerator"},
    {"question": "I have keys but no locks, and a space but no room. You can enter, but there’s no exit. What am I?", "answer": "keyboard"},
    {"question": "I get wet while I dry others. I am used after a bath or washing dishes. What am I?", "answer": "towel"},
    {"question": "I have hands but no fingers, and I tell you the time all day long. What am I?", "answer": "clock"},
    {"question": "I go up and up, but I never come down. Everyone experiences me as time passes. What am I?", "answer": "age"},
    {"question": "I have a head and a tail, but no body in between. I am often flipped to make decisions. What am I?", "answer": "coin"},
    {"question": "I travel the world while staying in one place, often found on an envelope’s face. What am I?", "answer": "stamp"},
    {"question": "I have many teeth, but I cannot bite. I am used to groom your hair just right. What am I?", "answer": "comb"},
    {"question": "I break every day, but I never fall. I signal the start of a new dawn. What am I?", "answer": "dawn"},
    {"question": "I fall every night, but I never break. I bring darkness when I take my place. What am I?", "answer": "night"},
    {"question": "I have a mouth but cannot eat, I flow through valleys, wide and deep. What am I?", "answer": "river"},
    {"question": "I am black when you buy me, red when you use me, and gray when you discard me. What am I?", "answer": "charcoal"},
    {"question": "I can be given away but still kept, and I light up faces when I’m expressed. What am I?", "answer": "smile"},
    {"question": "I have legs but cannot walk, I stand still in your dining hall. What am I?", "answer": "table"},
    {"question": "I am so fragile that saying my name will break me. I am the absence of sound. What am I?", "answer": "silence"},
    {"question": "I have a bottom at the top, and you find me on your body. What am I?", "answer": "leg"},
    {"question": "I can fill a room but take no space, and I make things visible in every place. What am I?", "answer": "light"},
    {"question": "I have keys but cannot play music, and I’m used to write letters in a hurry. What am I?", "answer": "typewriter"},
    {"question": "I come once in a minute, twice in a moment, but never in a thousand years. What am I?", "answer": "m"},
    {"question": "I am always old but never new, a record of the past that’s true. What am I?", "answer": "history"},
    {"question": "I am taken before you get it, capturing moments in a flash. What am I?", "answer": "photograph"},
    {"question": "I have wings but cannot fly, waddling on ice under the sky. What am I?", "answer": "penguin"},
    {"question": "I am easy to get into but hard to escape, often causing trouble or a scrape. What am I?", "answer": "trouble"},
    {"question": "I am always coming but never arrive, you wait for me, but I pass by. What am I?", "answer": "tomorrow"},
    {"question": "I can be broken with a single word, often felt deeply in the heart. What am I?", "answer": "heart"},
    {"question": "I get bigger the more you take away, and I’m found in the ground every day. What am I?", "answer": "hole"},
    {"question": "I have feet but no toes, and I measure things wherever I go. What am I?", "answer": "ruler"},
    {"question": "I can be made, but no one sees me, not even you, though you hear me. What am I?", "answer": "noise"},
    {"question": "I am alive but drink no water, consuming all in my fiery slaughter. What am I?", "answer": "fire"},
    {"question": "I can be touched but not seen, all around you, I’m always clean. What am I?", "answer": "air"},
    {"question": "I am heavy when read forward, but not when read backward. What am I?", "answer": "ton"},
    {"question": "I am full all day but empty at night, slipped on and off with little fight. What am I?", "answer": "shoe"},
    {"question": "I have a roof but no walls, found in fields, I stand quite small. What am I?", "answer": "mushroom"},
    {"question": "I follow you everywhere, you hear but don’t see me, I’m yours alone. What am I?", "answer": "voice"},
    {"question": "I am a word of three letters, I mean to depart, but add two letters, and I become a place to rest. What am I?", "answer": "bed"},
    {"question": "I am present in every house, but I’m not furniture. I’m always moving, but I never leave. What am I?", "answer": "air"},
    {"question": "I am where the earth and sky appear to meet, never reached no matter how far you go. What am I?", "answer": "horizon"},
    {"question": "I am a box without hinges, key, or lid, yet inside me, a golden treasure is hid. What am I?", "answer": "egg"},
    {"question": "I am not alive, but I grow; I don’t have lungs, but I need air; I don’t have a mouth, but water kills me. What am I?", "answer": "fire"},
    {"question": "I am always silent, but I can be loud when opened. I hold stories, knowledge, and more. What am I?", "answer": "book"},
    {"question": "I am a place where dreams are born, yet I’m gone by the light of morn. What am I?", "answer": "sleep"},
    {"question": "I am found on your body, but I’m not a limb. I’m often covered, but not with skin. What am I?", "answer": "neck"},
    {"question": "I am round, but not a ball, used in games, but I don’t fall. What am I?", "answer": "coin"},
    {"question": "I am a bridge with no river, found on your face, holding lenses. What am I?", "answer": "glasses"},
    {"question": "I am sharp, but I don’t cut; I’m in your head, and I’m used in a rut. What am I?", "answer": "wit"},
    {"question": "I am a chain, but I don’t bind; I’m on a bike, helping it grind. What am I?", "answer": "chain"},
    {"question": "I am bright but give no light, I’m on your face when things go right. What am I?", "answer": "smile"},
    {"question": "I am long and thin, but I don’t grow; I’m used to measure, steady and slow. What am I?", "answer": "ruler"},
    {"question": "I am deep, but I don’t sink; I’m in your mind when you think. What am I?", "answer": "thought"},
    {"question": "I am soft, but you can’t touch me; I’m heard in whispers, quiet and free. What am I?", "answer": "voice"},
    {"question": "I am a ring, but not for a finger; I make a sound when you make me linger. What am I?", "answer": "bell"},
    {"question": "I am heavy, but I weigh nothing; I’m felt in your heart when guilt is pressing. What am I?", "answer": "burden"},
    {"question": "I am flat, but I don’t lie; I’m in your kitchen, where plates fly. What am I?", "answer": "table"},
    {"question": "I am cold, but I don’t freeze; I’m a breeze that makes you sneeze. What am I?", "answer": "wind"},
    {"question": "I am a key, but I don’t unlock; I’m on a map, not a clock. What am I?", "answer": "legend"},
    {"question": "I am bright, but I don’t shine; I’m an idea that feels divine. What am I?", "answer": "thought"},
    {"question": "I am wide, but not deep; I’m a smile that you keep. What am I?", "answer": "smile"},
    {"question": "I am empty, but never light; I growl when you skip a bite. What am I?", "answer": "stomach"},
    {"question": "I am fast, but I don’t move; I’m in your dreams, in a groove. What am I?", "answer": "dream"},
    {"question": "I am a crown, but not for a king; I’m on a tooth, a shiny thing. What am I?", "answer": "crown"},
    {"question": "I am sharp, but I don’t cut; I’m a pain that’s felt in the gut. What am I?", "answer": "pain"},
    {"question": "I am a tail, but not on a beast; I trail behind, in the sky at least. What am I?", "answer": "comet"},
    {"question": "I am deep, but I don’t drown; I’m where you go when you’re lying down. What am I?", "answer": "sleep"},
    {"question": "I am a frame, but I hold no art; I’m around your bed, where you rest your heart. What am I?", "answer": "bed"},
    {"question": "I am loud, but I don’t speak; I’m heard when storms are at their peak. What am I?", "answer": "thunder"},
    {"question": "I am a ring, but not for a call; I’m around your neck, not small at all. What am I?", "answer": "necklace"},
    {"question": "I am heavy, but I don’t sink; I’m a cloud that makes you think. What am I?", "answer": "cloud"},
    {"question": "I am a foot, but I don’t walk; I’m at the base of a hill, not chalk. What am I?", "answer": "foothill"},
    {"question": "I am bright, but I don’t glow; I’m a vision of what’s to come, you know. What am I?", "answer": "future"},
    {"question": "I am a chain, but I don’t bind; I’m on a watch, keeping time in line. What am I?", "answer": "chain"},
    {"question": "I am soft, but you can’t feel me; I’m a whisper that travels free. What am I?", "answer": "whisper"},
    {"question": "I am a lid, but not on a jar; I’m on a pot, where you cook from afar. What am I?", "answer": "lid"},
    {"question": "I am sweet, but not to taste; I’m a memory that’s never erased. What am I?", "answer": "memory"},
    {"question": "I am a tongue, but I don’t speak; I’m in a flame, dancing and sleek. What am I?", "answer": "flame"},
    {"question": "I am hot, but I don’t warm; I’m a spice that can cause a storm. What am I?", "answer": "pepper"},
    {"question": "I am a head, but I have no face; I’m on a coin, in a common place. What am I?", "answer": "head"},
    {"question": "I am flat, but not smooth; I’m a desert where sands move. What am I?", "answer": "desert"},
    {"question": "I am a nose, but I don’t smell; I’m on a plane, where I dwell. What am I?", "answer": "nose"},
    {"question": "I am full, but I don’t overflow; I’m the sky where stars glow. What am I?", "answer": "sky"},
    {"question": "I am a mouth, but I don’t eat; I’m a cave where echoes meet. What am I?", "answer": "cave"},
    {"question": "I am old, but I don’t age; I’m a stone from a bygone stage. What am I?", "answer": "stone"},
    {"question": "I am a floor, but not in a house; I’m a forest where creatures browse. What am I?", "answer": "floor"},
    {"question": "I am sharp, but I don’t cut; I’m a tongue that speaks with gut. What am I?", "answer": "tongue"},
    {"question": "I am a wing, but I don’t fly; I’m on a plane that soars high. What am I?", "answer": "wing"},
    {"question": "I am tall, but I don’t stand; I’m a story that’s grand. What am I?", "answer": "story"},
    {"question": "I am a heart, but I don’t beat; I’m in a peach, a tasty treat. What am I?", "answer": "heart"},
    {"question": "I am cold, but I don’t chill; I’m a wind that gives a thrill. What am I?", "answer": "wind"},
    {"question": "I am a key, but I don’t lock; I’m on a piano, tick-tock. What am I?", "answer": "key"},
    {"question": "I am bright, but I don’t shine; I’m a star in the night’s design. What am I?", "answer": "star"},
    {"question": "I am a spine, but not in a back; I’m in a book on a rack. What am I?", "answer": "spine"},
    {"question": "I am wide, but not deep; I’m a river where secrets keep. What am I?", "answer": "river"},
    {"question": "I am a face, but I don’t smile; I’m on a watch, ticking all the while. What am I?", "answer": "face"},
    {"question": "I am empty, but never bare; I’m a space with nothing there. What am I?", "answer": "space"},
    {"question": "I am a neck, but I don’t turn; I’m on a bottle where liquids churn. What am I?", "answer": "neck"},
    {"question": "I am fast, but I don’t run; I’m light that comes from the sun. What am I?", "answer": "light"},
    {"question": "I am a crown, but not for a head; I’m on a hill where paths are led. What am I?", "answer": "crown"},
    {"question": "I am sharp, but I don’t pierce; I’m a wit that’s fierce. What am I?", "answer": "wit"},
    {"question": "I am a tail, but not on a beast; I’m on a kite, flying east. What am I?", "answer": "tail"},
    {"question": "I am deep, but I don’t fall; I’m an ocean, vast and tall. What am I?", "answer": "ocean"},
    {"question": "I am a frame, but I hold no picture; I’m a window with a view much richer. What am I?", "answer": "window"},
    {"question": "I am loud, but I don’t shout; I’m a wave that crashes about. What am I?", "answer": "wave"},
    {"question": "I am a ring, but not for a finger; I’m a halo where angels linger. What am I?", "answer": "halo"},
    {"question": "I am heavy, but I don’t drop; I’m a fog that sits on top. What am I?", "answer": "fog"},
    {"question": "I am a foot, but I don’t step; I’m a base where mountains are kept. What am I?", "answer": "foot"},
    {"question": "I am bright, but I don’t dazzle; I’m a color that doesn’t frazzle. What am I?", "answer": "color"},
    {"question": "I am a chain, but I don’t bind; I’m on a swing, fun to find. What am I?", "answer": "chain"},
    {"question": "I am soft, but not plush; I’m a feather that falls with a hush. What am I?", "answer": "feather"},
    {"question": "I am a lid, but not on a box; I’m on a chest with no locks. What am I?", "answer": "lid"},
    {"question": "I am sweet, but not candy; I’m a kiss that’s always handy. What am I?", "answer": "kiss"},
    {"question": "I am a tongue, but I don’t taste; I’m in a shoe, tied in haste. What am I?", "answer": "tongue"},
    {"question": "I am hot, but I don’t cook; I’m a trend that’s worth a look. What am I?", "answer": "trend"},
    {"question": "I am a head, but I have no brain; I’m on a nail, driven with pain. What am I?", "answer": "head"},
    {"question": "I am flat, but not even; I’m a pancake, freshly leavened. What am I?", "answer": "pancake"},
    {"question": "I am a nose, but I don’t breathe; I’m on a teapot, steam to wreathe. What am I?", "answer": "nose"},
    {"question": "I am full, but I don’t spill; I’m a lake on a hill. What am I?", "answer": "lake"},
    {"question": "I am a mouth, but I don’t speak; I’m a jar where you peek. What am I?", "answer": "mouth"},
    {"question": "I am old, but I don’t rust; I’m gold, a treasure you trust. What am I?", "answer": "gold"},
    {"question": "I am a floor, but not tiled; I’m a meadow where creatures are wild. What am I?", "answer": "meadow"},
    {"question": "I am sharp, but I don’t wound; I’m a glance that’s never swooned. What am I?", "answer": "glance"},
    {"question": "I am a wing, but I don’t soar; I’m on a windmill, spinning more. What am I?", "answer": "blade"},
    {"question": "I am tall, but I don’t climb; I’m a pole that marks the time. What am I?", "answer": "pole"},
    {"question": "I am a heart, but I don’t love; I’m in an apple, fit like a glove. What am I?", "answer": "core"},
    {"question": "I am cold, but I don’t shiver; I’m an iceberg in a river. What am I?", "answer": "iceberg"},
    {"question": "I am a key, but I don’t open; I’m a note in a song, softly spoken. What am I?", "answer": "note"},
    {"question": "I am bright, but I don’t flash; I’m a dream that doesn’t crash. What am I?", "answer": "dream"},
    {"question": "I am a spine, but not in a back; I’m a ridge on a mountain track. What am I?", "answer": "ridge"},
    {"question": "I am wide, but not vast; I’m a plain that stretches fast. What am I?", "answer": "plain"},
    {"question": "I am a face, but I don’t grin; I’m a mask where secrets begin. What am I?", "answer": "mask"},
    {"question": "I am empty, but never blank; I’m a room where thoughts are sank. What am I?", "answer": "room"},
    {"question": "I am a neck, but I don’t turn; I’m on a guitar where strings burn. What am I?", "answer": "neck"},
    {"question": "I am fast, but I don’t race; I’m a pulse in your chest’s space. What am I?", "answer": "pulse"},
    {"question": "I am a crown, but not royal; I’m on a flower, bright and loyal. What am I?", "answer": "crown"},
    {"question": "I am sharp, but I don’t sting; I’m a focus that makes you sing. What am I?", "answer": "focus"},
    {"question": "I am a tail, but I don’t end; I’m a trail where paths bend. What am I?", "answer": "trail"},
    {"question": "I am deep, but I don’t dive; I’m a mind where thoughts thrive. What am I?", "answer": "mind"},
    {"question": "I am a frame, but I hold no art; I’m a gate where journeys start. What am I?", "answer": "gate"},
    {"question": "I am loud, but I don’t yell; I’m a drum that rings a spell. What am I?", "answer": "drum"},
    {"question": "I am a ring, but not round; I’m a sound that’s all around. What am I?", "answer": "sound"},
    {"question": "I am heavy, but I don’t fall; I’m a mist that covers all. What am I?", "answer": "mist"},
    {"question": "I am a foot, but I don’t stride; I’m a meter in a poem’s ride. What am I?", "answer": "meter"},
    {"question": "I am bright, but I don’t glow; I’m a hue in a rainbow’s show. What am I?", "answer": "hue"},
    {"question": "I am a chain, but I don’t bind; I’m a stitch in a quilt’s design. What am I?", "answer": "stitch"},
    {"question": "I am soft, but I don’t yield; I’m silk in a fabric field. What am I?", "answer": "silk"},
    {"question": "I am a lid, but I don’t cover; I’m a hat on a head, like no other. What am I?", "answer": "hat"},
    {"question": "I am sweet, but not sugary; I’m a song that’s light and airy. What am I?", "answer": "song"},
    {"question": "I am a tongue, but I don’t taste; I’m a flag that flaps in haste. What am I?", "answer": "flag"},
    {"question": "I am hot, but I don’t flame; I’m a coal in a fire’s game. What am I?", "answer": "coal"},
    {"question": "I am a head, but I don’t think; I’m a pin at the edge of a brink. What am I?", "answer": "head"},
    {"question": "I am flat, but not plain; I’m a sheet where dreams remain. What am I?", "answer": "sheet"},
    {"question": "I am a nose, but I don’t sniff; I’m on a ship that’s stiff. What am I?", "answer": "bow"},
    {"question": "I am full, but not crowded; I’m a field where dreams are shrouded. What am I?", "answer": "field"},
    {"question": "I am a mouth, but I don’t talk; I’m a stream where waters walk. What am I?", "answer": "mouth"},
    {"question": "I am old, but I don’t fade; I’m a legend that’s always made. What am I?", "answer": "legend"},
    {"question": "I am a floor, but not grounded; I’m a platform where ideas are founded. What am I?", "answer": "platform"},
    {"question": "I am sharp, but I don’t slash; I’m a look that sparks a clash. What am I?", "answer": "look"},
    {"question": "I am a wing, but I don’t fly; I’m a fin in the ocean’s sigh. What am I?", "answer": "fin"},
    {"question": "I am tall, but I don’t tower; I’m a giraffe with gentle power. What am I?", "answer": "giraffe"},
    {"question": "I am a heart, but I don’t beat; I’m a center, calm and neat. What am I?", "answer": "center"},
    {"question": "I am cold, but I don’t frost; I’m a stare that’s never lost. What am I?", "answer": "stare"},
    {"question": "I am a key, but I don’t lock; I’m a scale in music’s stock. What am I?", "answer": "scale"},
    {"question": "I am bright, but I don’t beam; I’m a gleam in a hopeful dream. What am I?", "answer": "gleam"},
    {"question": "I am a spine, but not flesh; I’m a porcupine’s quills, fresh. What am I?", "answer": "spine"},
    {"question": "I am wide, but not broad; I’m a bay where ships are stored. What am I?", "answer": "bay"},
    {"question": "I am a face, but I don’t smile; I’m a cliff with a rocky style. What am I?", "answer": "cliff"},
    {"question": "I am empty, but never void; I’m a gap where thoughts are toyed. What am I?", "answer": "gap"},
    {"question": "I am a neck, but not human; I’m on a swan, graceful and true, man. What am I?", "answer": "neck"},
    {"question": "I am fast, but I don’t hurry; I’m a current in a river’s flurry. What am I?", "answer": "current"},
    {"question": "I am a crown, but not for kings; I’m a cap on a bottle’s springs. What am I?", "answer": "cap"},
    {"question": "I am sharp, but I don’t bite; I’m sarcasm with a witty light. What am I?", "answer": "sarcasm"}
],
    

   



    "word_games": [
        {"question": "What is the opposite of 'hot'?", "answer": "cold"},
        {"question": "What word rhymes with 'cat'?", "answer": "bat"},
        {"question": "How many letters are in the word 'COMPUTER'?", "answer": "8"},
        {"question": "What is the plural of 'mouse' (animal)?", "answer": "mice"},
        {"question": "What word means the same as 'big'?", "answer": "large"},
        {"question": "What is an anagram of 'LISTEN'?", "answer": "silent"},
        {"question": "What letter comes after 'M' in the alphabet?", "answer": "n"},
        {"question": "What word is spelled backwards as 'STRESSED'?", "answer": "desserts"},
        {"question": "How many vowels are in 'EDUCATION'?", "answer": "5"},
        {"question": "What is the past tense of 'run'?", "answer": "ran"},
        {"question": "What is the opposite of 'up'?", "answer": "down"},
        {"question": "What word rhymes with 'moon'?", "answer": "spoon"},
        {"question": "How many letters are in the word 'SUNSHINE'?", "answer": "8"},
        {"question": "What is the plural of 'child'?", "answer": "children"},
        {"question": "What word means the same as 'happy'?", "answer": "joyful"},
        {"question": "What is an anagram of 'RACE'?", "answer": "care"},
        {"question": "What letter comes before 'P' in the alphabet?", "answer": "o"},
        {"question": "What word is spelled backwards as 'DEKAB'?", "answer": "baked"},
        {"question": "How many vowels are in 'UMBRELLA'?", "answer": "3"},
        {"question": "What is the past tense of 'sing'?", "answer": "sang"},
        {"question": "What is the opposite of 'fast'?", "answer": "slow"},
        {"question": "What word rhymes with 'tree'?", "answer": "free"},
        {"question": "How many letters are in the word 'KITCHEN'?", "answer": "7"},
        {"question": "What is the plural of 'goose'?", "answer": "geese"},
        {"question": "What word means the same as 'small'?", "answer": "tiny"},
        {"question": "What is an anagram of 'STOP'?", "answer": "post"},
        {"question": "What letter comes after 'Y' in the alphabet?", "answer": "z"},
        {"question": "What word is spelled backwards as 'EVOL'?", "answer": "love"},
        {"question": "How many vowels are in 'PICTURE'?", "answer": "3"},
        {"question": "What is the past tense of 'drink'?", "answer": "drank"},
        {"question": "What is the opposite of 'open'?", "answer": "closed"},
        {"question": "What word rhymes with 'day'?", "answer": "play"},
        {"question": "How many letters are in the word 'GARDEN'?", "answer": "6"},
        {"question": "What is the plural of 'leaf'?", "answer": "leaves"},
        {"question": "What word means the same as 'quick'?", "answer": "fast"},
        {"question": "What is an anagram of 'HEART'?", "answer": "earth"},
        {"question": "What letter comes before 'G' in the alphabet?", "answer": "f"},
        {"question": "What word is spelled backwards as 'RATS'?", "answer": "star"},
        {"question": "How many vowels are in 'APPLE'?", "answer": "2"},
        {"question": "What is the past tense of 'write'?", "answer": "wrote"},
        {"question": "What is the opposite of 'light' (brightness)?", "answer": "dark"},
        {"question": "What word rhymes with 'book'?", "answer": "look"},
        {"question": "How many letters are in the word 'WINDOW'?", "answer": "6"},
        {"question": "What is the plural of 'sheep'?", "answer": "sheep"},
        {"question": "What word means the same as 'calm'?", "answer": "peaceful"},
        {"question": "What is an anagram of 'DEBIT'?", "answer": "bited"},
        {"question": "What letter comes after 'J' in the alphabet?", "answer": "k"},
        {"question": "What word is spelled backwards as 'DEED'?", "answer": "deed"},
        {"question": "How many vowels are in 'ORANGE'?", "answer": "3"},
        {"question": "What is the past tense of 'go'?", "answer": "went"},
        {"question": "What is the opposite of 'near'?", "answer": "far"},
        {"question": "What word rhymes with 'star'?", "answer": "car"},
        {"question": "How many letters are in the word 'PIANO'?", "answer": "5"},
        {"question": "What is the plural of 'foot'?", "answer": "feet"},
        {"question": "What word means the same as 'beautiful'?", "answer": "pretty"},
        {"question": "What is an anagram of 'NIGHT'?", "answer": "thing"},
        {"question": "What letter comes before 'V' in the alphabet?", "answer": "u"},
        {"question": "What word is spelled backwards as 'WON'?", "answer": "now"},
        {"question": "How many vowels are in 'SCHOOL'?", "answer": "3"},
        {"question": "What is the past tense of 'read'?", "answer": "read"}
    ],

  

    "movies": [
        {"question": "Who directed the movie 'Titanic'?", "answer": "james cameron"},
        {"question": "What movie features the quote 'May the Force be with you'?", "answer": "star wars"},
        {"question": "Which movie won the Academy Award for Best Picture in 2020?", "answer": "parasite"},
        {"question": "Who played Jack Sparrow in Pirates of the Caribbean?", "answer": "johnny depp"},
        {"question": "What is the highest-grossing movie of all time?", "answer": "avatar"},
        {"question": "In which movie do we hear 'Here's looking at you, kid'?", "answer": "casablanca"},
        {"question": "What movie features a young wizard named Harry?", "answer": "harry potter"},
        {"question": "Who directed 'The Dark Knight'?", "answer": "christopher nolan"},
        {"question": "What animated movie features Elsa and Anna?", "answer": "frozen"},
        {"question": "Which movie series features Dominic Toretto?", "answer": "fast and furious"},
        {"question": "Who directed 'Schindler's List'?", "answer": "steven spielberg"},
        {"question": "What movie features the quote 'You can't handle the truth!'?", "answer": "a few good men"},
        {"question": "Which movie won the Academy Award for Best Picture in 1994?", "answer": "forrest gump"},
        {"question": "Who played the Joker in 'The Dark Knight'?", "answer": "heath ledger"},
        {"question": "What is the highest-grossing animated movie of all time?", "answer": "the lion king"},
        {"question": "In which movie is the line 'I'm king of the world!' shouted?", "answer": "titanic"},
        {"question": "What movie features Woody and Buzz Lightyear?", "answer": "toy story"},
        {"question": "Who directed 'Pulp Fiction'?", "answer": "quentin tarantino"},
        {"question": "What movie is set in the fictional land of Arendelle?", "answer": "frozen"},
        {"question": "Which movie features a character named Tony Stark?", "answer": "iron man"},
        {"question": "What is the name of the ship in 'Jaws'?", "answer": "orca"},
        {"question": "Who played Scarlett O'Hara in 'Gone with the Wind'?", "answer": "vivien leigh"},
        {"question": "What movie features the quote 'I'll be back'?", "answer": "the terminator"},
        {"question": "Which movie won the Academy Award for Best Picture in 2017?", "answer": "moonlight"},
        {"question": "Who played Neo in 'The Matrix'?", "answer": "keanu reeves"},
        {"question": "What animated movie features a lion named Simba?", "answer": "the lion king"},
        {"question": "Who directed 'Inception'?", "answer": "christopher nolan"},
        {"question": "What movie features the quote 'Life is like a box of chocolates'?", "answer": "forrest gump"},
        {"question": "Which movie series includes the character Katniss Everdeen?", "answer": "the hunger games"},
        {"question": "What is the name of the fictional magazine in 'The Devil Wears Prada'?", "answer": "runway"},
        {"question": "Who played Vito Corleone in 'The Godfather'?", "answer": "marlon brando"},
        {"question": "What movie features the quote 'Nobody puts Baby in a corner'?", "answer": "dirty dancing"},
        {"question": "Which movie won the Academy Award for Best Picture in 2008?", "answer": "slumdog millionaire"},
        {"question": "Who played Hermione Granger in the 'Harry Potter' series?", "answer": "emma watson"},
        {"question": "What animated movie features a clownfish named Nemo?", "answer": "finding nemo"},
        {"question": "Who directed 'Citizen Kane'?", "answer": "orson welles"},
        {"question": "What movie features the quote 'Fasten your seatbelts; it's going to be a bumpy night'?", "answer": "all about eve"},
        {"question": "Which movie series includes the character Ethan Hunt?", "answer": "mission: impossible"},
        {"question": "What is the name of the fictional African nation in 'Black Panther'?", "answer": "wakanda"},
        {"question": "Who played Ellen Ripley in 'Alien'?", "answer": "sigourney weaver"},
        {"question": "What movie features the quote 'There's no place like home'?", "answer": "the wizard of oz"},
        {"question": "Which movie won the Academy Award for Best Picture in 1997?", "answer": "titanic"},
        {"question": "Who played the title role in 'Forrest Gump'?", "answer": "tom hanks"},
        {"question": "What animated movie features a rat named Remy who loves to cook?", "answer": "ratatouille"},
        {"question": "Who directed 'The Shawshank Redemption'?", "answer": "frank darabont"},
        {"question": "What movie features the quote 'My precious'?", "answer": "the lord of the rings"},
        {"question": "Which movie includes the character Clarice Starling?", "answer": "the silence of the lambs"},
        {"question": "What is the name of the boat in 'Willy Wonka & the Chocolate Factory'?", "answer": "wonkatania"},
        {"question": "Who played Indiana Jones in 'Raiders of the Lost Ark'?", "answer": "harrison ford"},
        {"question": "What movie features the quote 'Houston, we have a problem'?", "answer": "apollo 13"},
        {"question": "Which movie won the Academy Award for Best Picture in 2019?", "answer": "green book"},
        {"question": "Who played Marge Gunderson in 'Fargo'?", "answer": "frances mcdormand"},
        {"question": "What animated movie features a robot named WALL-E?", "answer": "wall-e"},
        {"question": "Who directed 'Jurassic Park'?", "answer": "steven spielberg"},
        {"question": "What movie features the quote 'You're gonna need a bigger boat'?", "answer": "jaws"},
        {"question": "Which movie series includes the character Luke Skywalker?", "answer": "star wars"},
        {"question": "What is the name of the school in 'Dead Poets Society'?", "answer": "welton academy"},
        {"question": "Who played Maximus in 'Gladiator'?", "answer": "russell crowe"},
        {"question": "What movie features the quote 'I see dead people'?", "answer": "the sixth sense"},
        {"question": "Which movie won the Academy Award for Best Picture in 2012?", "answer": "the artist"},
        {"question": "Who played the title role in 'Erin Brockovich'?", "answer": "julia roberts"},
        {"question": "What animated movie features a panda named Po?", "answer": "kung fu panda"},
        {"question": "Who directed 'La La Land'?", "answer": "damien chazelle"},
        {"question": "What movie features the quote 'Carpe diem. Seize the day, boys'?", "answer": "dead poets society"},
        {"question": "Which movie series includes the character Bella Swan?", "answer": "twilight"},
        {"question": "What is the name of the fictional city in 'Batman' movies?", "answer": "gotham"},
        {"question": "Who played Rose DeWitt Bukater in 'Titanic'?", "answer": "kate winslet"},
        {"question": "What movie features the quote 'Why so serious?'?", "answer": "the dark knight"},
        {"question": "Which movie won the Academy Award for Best Picture in 2015?", "answer": "birdman"},
        {"question": "Who played Andy Dufresne in 'The Shawshank Redemption'?", "answer": "tim robbins"},
        {"question": "What animated movie features a blue tang fish named Dory?", "answer": "finding dory"},
        {"question": "Who directed 'E.T. the Extra-Terrestrial'?", "answer": "steven spielberg"},
        {"question": "What movie features the quote 'Keep your friends close, but your enemies closer'?", "answer": "the godfather"},
        {"question": "Which movie series includes the character John Wick?", "answer": "john wick"},
        {"question": "What is the name of the fictional chocolate factory in 'Charlie and the Chocolate Factory'?", "answer": "wonka factory"},
        {"question": "Who played Rhett Butler in 'Gone with the Wind'?", "answer": "clark gable"},
        {"question": "What movie features the quote 'Just keep swimming'?", "answer": "finding nemo"},
        {"question": "Which movie won the Academy Award for Best Picture in 2023?", "answer": "oppenheimer"},
        {"question": "Who played the title role in 'Bohemian Rhapsody'?", "answer": "rami malek"},
        {"question": "What animated movie features a snowman named Olaf?", "answer": "frozen"},
        {"question": "Who directed 'The Godfather'?", "answer": "francis ford coppola"},
        {"question": "What movie features the quote 'To infinity and beyond!'?", "answer": "toy story"},
        {"question": "Which movie series includes the character Marty McFly?", "answer": "back to the future"},
        {"question": "What is the name of the motel in 'Psycho'?", "answer": "bates motel"},
        {"question": "Who played Mia Wallace in 'Pulp Fiction'?", "answer": "uma thurman"},
        {"question": "What movie features the quote 'Hakuna matata'?", "answer": "the lion king"},
        {"question": "Which movie won the Academy Award for Best Picture in 2004?", "answer": "million dollar baby"},
        {"question": "Who played Atticus Finch in 'To Kill a Mockingbird'?", "answer": "gregory peck"},
        {"question": "What animated movie features a dragon named Mushu?", "answer": "mulan"},
        {"question": "Who directed 'Avatar: The Way of Water'?", "answer": "james cameron"},
        {"question": "What movie features the quote 'I am Groot'?", "answer": "guardians of the galaxy"},
        {"question": "Which movie series includes the character Jason Bourne?", "answer": "bourne"},
        {"question": "What is the name of the fictional wizarding school in 'Harry Potter'?", "answer": "hogwarts"},
        {"question": "Who played J. Robert Oppenheimer in 'Oppenheimer'?", "answer": "cillian murphy"},
        {"question": "What movie features the quote 'Show me the money!'?", "answer": "jerry maguire"},
        {"question": "Which movie won the Academy Award for Best Picture in 1990?", "answer": "dances with wolves"},
        {"question": "Who played Sarah Connor in 'Terminator 2: Judgment Day'?", "answer": "linda hamilton"},
        {"question": "What animated movie features a genie voiced by Robin Williams?", "answer": "aladdin"},
        {"question": "What Bollywood movie features the quote 'Mere paas maa hai'?", "answer": "deewar"},
        {"question": "Who played Vijay in 'Deewar'?", "answer": "amitabh bachchan"},
        {"question": "What movie features the quote 'Kitne aadmi the?'?", "answer": "sholay"},
        {"question": "Who played Gabbar Singh in 'Sholay'?", "answer": "amjad khan"},
        {"question": "What Bollywood movie features the quote 'Mogambo khush hua'?", "answer": "mr. india"},
        {"question": "Who played Mogambo in 'Mr. India'?", "answer": "amrish puri"},
        {"question": "What movie features the quote 'Bade bade deshon mein aisi choti choti baatein hoti rehti hai, Senorita'?", "answer": "dilwale dulhania le jayenge"},
        {"question": "Who played Raj in 'Dilwale Dulhania Le Jayenge'?", "answer": "shah rukh khan"},
        {"question": "What Bollywood movie features the quote 'Mein apni favourite hoon'?", "answer": "jab we met"},
        {"question": "Who played Geet in 'Jab We Met'?", "answer": "kareena kapoor"},
        {"question": "What movie features the quote 'Picture abhi baaki hai mere dost'?", "answer": "om shanti om"},
        {"question": "Who played Om Prakash Makhija in 'Om Shanti Om'?", "answer": "shah rukh khan"},
        {"question": "What Bollywood movie features the quote 'Crime Master Gogo naam hai mera, aankhen nikal ke gotiyan khelta hun main'?", "answer": "andaz apna apna"},
        {"question": "Who played Crime Master Gogo in 'Andaz Apna Apna'?", "answer": "shakti kapoor"},
        {"question": "Who directed the Bollywood movie '3 Idiots'?", "answer": "rajkumar hirani"},
        {"question": "What movie features the quote 'All izz well'?", "answer": "3 idiots"},
        {"question": "Who played Rancho in '3 Idiots'?", "answer": "aamir khan"},
        {"question": "What Bollywood movie features the quote 'Tareekh pe tareekh, tareekh pe tareekh'?", "answer": "damini"},
        {"question": "Who played Damini in 'Damini'?", "answer": "meenakshi sheshadri"},
        {"question": "What movie features the quote 'Pushpa, I hate tears'?", "answer": "amar prem"},
        {"question": "Who played Anand Babu in 'Amar Prem'?", "answer": "rajesh khanna"},
        {"question": "Who directed the Bollywood movie 'Lagaan'?", "answer": "ashutosh gowariker"},
        {"question": "What movie features the quote 'Kutte kaminey main tera khoon pee jaunga'?", "answer": "yaadon ki baraat"},
        {"question": "Who played Shankar in 'Yaadon Ki Baraat'?", "answer": "dharmendra"},
        {"question": "What Bollywood movie features the quote 'Rahul, naam toh suna hi hoga'?", "answer": "dil to pagal hai"},
        {"question": "Who played Rahul in 'Dil To Pagal Hai'?", "answer": "shah rukh khan"},
        {"question": "What movie features the quote 'I can talk English, I can walk English, I can laugh English'?", "answer": "namak halaal"},
        {"question": "Who played Arjun Singh in 'Namak Halaal'?", "answer": "amitabh bachchan"},
        {"question": "What Bollywood movie features the quote 'Tum kya apne aap ko Mughal-e-Azam, hum log ko Anarkali samajhta hai be'?", "answer": "bade miyan chote miyan"},
        {"question": "Who played Arjun Singh in 'Bade Miyan Chote Miyan' (1998)?", "answer": "govinda"},
        {"question": "Who directed the Japanese movie 'Seven Samurai'?", "answer": "akira kurosawa"},
        {"question": "What movie features the quote 'We shall overcome'?", "answer": "gandhi"},
        {"question": "Who played Mahatma Gandhi in 'Gandhi'?", "answer": "ben kingsley"},
        {"question": "What South Korean movie features a family infiltrating a wealthy household?", "answer": "parasite"},
        {"question": "Who directed the South Korean movie 'Oldboy'?", "answer": "park chan-wook"},
        {"question": "What movie features the quote 'I'm not a smart man, but I know what love is'?", "answer": "forrest gump"},
        {"question": "Who played Amélie Poulain in the French movie 'Amélie'?", "answer": "audrey tautou"},
        {"question": "What Bollywood movie features the quote 'Aawaz neeche'?", "answer": "action replayy"},
        {"question": "Who played Kishen in 'Action Replayy'?", "answer": "akshay kumar"},
        {"question": "What movie features the quote 'You shot gun, me quick gun Murugun … Ati-pati-kati yenna rascala'?", "answer": "om shanti om"},
        {"question": "Who played Mukesh in 'Om Shanti Om'?", "answer": "shreyas talpade"},
        {"question": "What Bollywood movie features the quote 'Dost fail ho jaye toh dukh hota hai'?", "answer": "zindagi na milegi dobara"},
        {"question": "Who played Imran in 'Zindagi Na Milegi Dobara'?", "answer": "farhan akhtar"},
        {"question": "Who directed the Italian movie 'Life Is Beautiful'?", "answer": "roberto benigni"},
        {"question": "What movie features the quote 'Good morning, and in case I don't see ya, good afternoon, good evening, and good night!'?", "answer": "the truman show"},
        {"question": "Who played Truman Burbank in 'The Truman Show'?", "answer": "jim carrey"},
        {"question": "What Bollywood movie features the quote 'Inke haath main sone ka lota diya phir bhi ye bhikh hi mangenge'?", "answer": "phir hera pheri"},
        {"question": "Who played Baburao in 'Phir Hera Pheri'?", "answer": "paresh rawal"},
        {"question": "What movie features the quote 'This is Sparta!'?", "answer": "300"},
        {"question": "Who played Leonidas in '300'?", "answer": "gerard butler"},
        {"question": "What Bollywood movie features the quote 'Swagat nahi karoge aap hamara?'?", "answer": "dabangg 2"},
        {"question": "Who played Chulbul Pandey in 'Dabangg 2'?", "answer": "salman khan"},
        {"question": "Who directed the Mexican movie 'Pan's Labyrinth'?", "answer": "guillermo del toro"},
        {"question": "What movie features the quote 'I'm the king of the world!'?", "answer": "titanic"},
        {"question": "Who played Jack Dawson in 'Titanic'?", "answer": "leonardo dicaprio"},
        {"question": "What Bollywood movie features the quote 'Main to nanha sa pyaara sa chota sa bachcha hu'?", "answer": "chalba presumably"},
        {"question": "Who played Raja in 'Chalbaaz'?", "answer": "shakti kapoor"},
        {"question": "What movie features the quote 'Get to the chopper!'?", "answer": "predator"},
        {"question": "Who played Dutch in 'Predator'?", "answer": "arnold schwarzenegger"},
        {"question": "What Bollywood movie features the quote 'Tension lene ka nahi, sirf dene ka'?", "answer": "golmaal: fun unlimited"},
        {"question": "Who played Gopal in 'Golmaal: Fun Unlimited'?", "answer": "ajay devgn"},
        {"question": "What animated movie features a green ogre named Shrek?", "answer": "shrek"},
        {"question": "Who voiced Shrek in 'Shrek'?", "answer": "mike myers"},
        {"question": "What Bollywood movie features the quote 'Jaa Simran, jaa. Jeele apni zindagi'?", "answer": "dilwale dulhania le jayenge"},
        {"question": "Who played Simran's father in 'Dilwale Dulhania Le Jayenge'?", "answer": "amrish puri"},
        {"question": "Who directed the Spanish movie 'The Others'?", "answer": "alejandro amenábar"},
        {"question": "What movie features the quote 'I drink your milkshake!'?", "answer": "there will be blood"},
        {"question": "Who played Daniel Plainview in 'There Will Be Blood'?", "answer": "daniel day-lewis"},
        {"question": "What Bollywood movie features the quote 'Beta, tumse na ho payega'?", "answer": "gangs of wasseypur"},
        {"question": "Who played Ramadhir Singh in 'Gangs of Wasseypur'?", "answer": "tigmanshu dhulia"},
        {"question": "What movie features the quote 'Yippie-ki-yay, motherfucker!'?", "answer": "die hard"},
        {"question": "Who played John McClane in 'Die Hard'?", "answer": "bruce willis"},
        {"question": "What Bollywood movie features the quote 'Hum chhathi ka dhood yaad dila denge'?", "answer": "bol bachchan"},
        {"question": "Who played Prithviraj Raghuvanshi in 'Bol Bachchan'?", "answer": "ajay devgn"},
        {"question": "Who directed the French movie 'The Intouchables'?", "answer": "olivier nakache"},
        {"question": "What movie features the quote 'You had me at hello'?", "answer": "jerry maguire"},
        {"question": "Who played Dorothy Boyd in 'Jerry Maguire'?", "answer": "renée zellweger"},
        {"question": "What Bollywood movie features the quote 'Kauva kitna bhi washing machine mein naha le, bagula nahi banta'?", "answer": "hungama"},
        {"question": "Who played Kachra Seth in 'Hungama'?", "answer": "paresh rawal"},
        {"question": "What animated movie features a lion cub named Kiara?", "answer": "the lion king ii: simba's pride"},
        {"question": "Who voiced Simba in 'The Lion King' (1994)?", "answer": "matthew broderick"},
        {"question": "What Bollywood movie features the quote 'Aree baba wrong number hai to uthati kyo hai'?", "answer": "hera pheri"},
        {"question": "Who played Raju in 'Hera Pheri'?", "answer": "akshay kumar"},
        {"question": "Who directed the South Korean movie 'Memories of Murder'?", "answer": "bong joon-ho"},
        {"question": "What movie features the quote 'I'm walking here!'?", "answer": "midnight cowboy"},
        {"question": "Who played Ratso Rizzo in 'Midnight Cowboy'?", "answer": "dustin hoffman"},
        {"question": "What Bollywood movie features the quote 'Rishtey mein toh hum tumhare baap lagte hai, naam hai Shahenshaah'?", "answer": "shahenshah"},
        {"question": "Who played Shahenshah in 'Shahenshah'?", "answer": "amitabh bachchan"},
        {"question": "What movie features the quote 'I love the smell of napalm in the morning'?", "answer": "apocalypse now"},
        {"question": "Who played Colonel Kilgore in 'Apocalypse Now'?", "answer": "robert duvall"},
        {"question": "What Bollywood movie features the quote 'Ek chutki sindoor ki keemat tum kya jaano Ramesh Babu?'?", "answer": "om shanti om"},
        {"question": "Who played Shanti Priya in 'Om Shanti Om'?", "answer": "deepika padukone"},
        {"question": "Who directed the Indian movie 'Bajrangi Bhaijaan'?", "answer": "kabir khan"},
        {"question": "What movie features the quote 'With great power comes great responsibility'?", "answer": "spider-man"},
        {"question": "Who played Peter Parker in 'Spider-Man' (2002)?", "answer": "tobey maguire"},
        {"question": "What Bollywood movie features the quote 'Main toh peeta hoon ke bas saans le saku'?", "answer": "devdas"},
        {"question": "Who played Devdas in 'Devdas' (2002)?", "answer": "shah rukh khan"},
        {"question": "What animated movie features a demigod named Maui?", "answer": "moana"},
        {"question": "Who voiced Maui in 'Moana'?", "answer": "dwayne johnson"},
        {"question": "What Bollywood movie features the quote 'Don ko pakadna mushkil hi nahi, namumkin hai'?", "answer": "don"},
        {"question": "Who played Don in 'Don' (1978)?", "answer": "amitabh bachchan"},
        {"question": "Who directed the Japanese movie 'Spirited Away'?", "answer": "hayao miyazaki"},
        {"question": "What movie features the quote 'Here's Johnny!'?", "answer": "the shining"},
        {"question": "Who played Jack Torrance in 'The Shining'?", "answer": "jack nicholson"}
    ],



  
    "music": [
        {"question": "How many strings does a standard guitar have?", "answer": "6"},
        {"question": "Which instrument has 88 keys?", "answer": "piano"},
        {"question": "Who composed 'The Four Seasons'?", "answer": "vivaldi"},
        {"question": "What does 'forte' mean in music?", "answer": "loud"},
        {"question": "How many beats are in a whole note?", "answer": "4"},
        {"question": "What is the highest female singing voice?", "answer": "soprano"},
        {"question": "Which band released 'Bohemian Rhapsody'?", "answer": "queen"},
        {"question": "What instrument does Yo-Yo Ma famously play?", "answer": "cello"},
        {"question": "How many lines are on a musical staff?", "answer": "5"},
        {"question": "What genre of music originated in New Orleans?", "answer": "jazz"},
        {"question": "Which Indian composer is known for 'Jai Ho' from Slumdog Millionaire?", "answer": "a.r. rahman"},
        {"question": "What instrument is Ravi Shankar famous for playing?", "answer": "sitar"},
        {"question": "Which Beatles song features the lyric 'I once had a girl, or should I say, she once had me'?", "answer": "norwegian wood"},
        {"question": "Who sang 'Mundian To Bach Ke' featuring Jay-Z?", "answer": "panjabi mc"},
        {"question": "What genre of Indian music is associated with South India and intricate ragas?", "answer": "carnatic"},
        {"question": "Which Australian band released 'Down Under' in 1981?", "answer": "men at work"},
        {"question": "What Korean pop group is known for 'Dynamite'?", "answer": "bts"},
        {"question": "What instrument is central to Indonesian dangdut music?", "answer": "tabla"},
        {"question": "Which song by Arijit Singh includes the lyric 'Tum hi ho, ab tum hi ho'?", "answer": "tum hi ho"},
        {"question": "Who composed the Indian national anthem 'Jana Gana Mana'?", "answer": "rabindranath tagore"},
        {"question": "What genre of music did Bob Marley popularize?", "answer": "reggae"},
        {"question": "Which American artist sang 'Sweet Caroline'?", "answer": "neil diamond"},
        {"question": "What traditional Japanese instrument is a 13-stringed zither?", "answer": "koto"},
        {"question": "Which song by Diljit Dosanjh features the lyric 'Mainu lehenga, lehenga, lehenga'?", "answer": "laembadgini"},
        {"question": "Who is known as the 'King of Pop'?", "answer": "michael jackson"},
        {"question": "What Native American instrument is often used in ceremonial music?", "answer": "flute"},
        {"question": "Which British band released 'Brimful of Asha' in 1997?", "answer": "cornershop"},
        {"question": "What genre of music combines Indian classical with jazz, as pioneered by Shakti?", "answer": "fusion"},
        {"question": "Which Filipino pop group was nominated for a Billboard Music Award in 2021?", "answer": "sb19"},
        {"question": "What song by The Kinks features a sitar-like riff and the lyric 'And it really got me down'?", "answer": "see my friends"},
        {"question": "Who is the Indian singer behind 'Jalebi Baby'?", "answer": "tesher"},
        {"question": "What Australian artist sang 'Somebody That I Used to Know'?", "answer": "gotye"},
        {"question": "Which Indian music style is prominent in Bollywood films?", "answer": "hindustani"},
        {"question": "What song by Queen includes the lyric 'Is this the real life? Is this just fantasy?'?", "answer": "bohemian rhapsody"},
        {"question": "Who played the tabla in the Indian fusion band Shakti?", "answer": "zakir hussain"},
        {"question": "What genre of electronic music originated in Goa, India?", "answer": "goa trance"},
        {"question": "Which American rapper collaborated with A.R. Rahman on 'Gangsta Blues'?", "answer": "snoop dogg"},
        {"question": "What traditional Chinese instrument is a two-stringed fiddle?", "answer": "erhu"},
        {"question": "Which song by Badshah features the lyric 'Mundeya toh bach ke rahi'?", "answer": "mercy"},
        {"question": "Who composed 'Symphony No. 5'?", "answer": "beethoven"},
        {"question": "What genre of music is associated with the Native American powwow?", "answer": "pan-tribal"},
        {"question": "Which Indian singer is known for 'Mile Sur Mera Tumhara'?", "answer": "lata mangeshkar"},
        {"question": "What Australian singer released 'Dance Monkey'?", "answer": "tones and i"},
        {"question": "Which song by The Beatles features the lyric 'Sitar gently weeps'?", "answer": "within you without you"},
        {"question": "What Korean traditional music style features narrative singing called p’ansori?", "answer": "korean traditional"},
        {"question": "Who is the Indian singer behind 'Why This Kolaveri Di'?", "answer": "dhanush"},
        {"question": "What instrument is central to bhangra music?", "answer": "dhol"},
        {"question": "Which American band released 'Sweet Home Alabama'?", "answer": "lynyrd skynyrd"},
        {"question": "What genre of music did Ravi Shankar introduce to Western audiences?", "answer": "indian classical"},
        {"question": "Which song by A.R. Rahman includes the lyric 'Maa tujhe salaam'?", "answer": "vande mataram"},
        {"question": "What Australian band released 'Highway to Hell'?", "answer": "ac/dc"},
        {"question": "Which Indian artist collaborated with Norah Jones on 'Traces of You'?", "answer": "anoushka shankar"},
        {"question": "What genre of music is known for its use of the Persian tar and setar?", "answer": "persian"},
        {"question": "Who sang 'My Boy Lollipop' in 1964?", "answer": "millie small"},
        {"question": "What instrument is used in Native American peyote songs?", "answer": "water drum"},
        {"question": "Which Bollywood song by Shankar Mahadevan features the lyric 'Jhanjhariya yeh jhanak jaye'?", "answer": "jhanjhariya"},
        {"question": "What genre of music did John Coltrane fuse with Indian ragas?", "answer": "jazz"},
        {"question": "Which Australian artist sang 'Chandelier'?", "answer": "sia"},
        {"question": "What song by Panjabi MC features the lyric 'Mundian toh bach ke rahi'?", "answer": "mundian to bach ke"},
        {"question": "Who composed the opera 'Carmen'?", "answer": "bizet"},
        {"question": "What traditional Indian instrument is a long-necked lute used in Hindustani music?", "answer": "tanpura"},
        {"question": "Which American artist sang 'Rolling in the Deep'?", "answer": "adele"},
        {"question": "What genre of music is associated with the Filipino kundiman?", "answer": "filipino"},
        {"question": "Which song by Diljit Dosanjh features the lyric 'Do you know, baby, mainu kinna pyar'?", "answer": "do you know"},
        {"question": "What instrument is central to Japanese taiko music?", "answer": "drum"},
        {"question": "Who sang 'Soul Makossa' in 1972?", "answer": "manu dibango"},
        {"question": "What Indian music genre is known for devotional qawwali songs?", "answer": "sufi"},
        {"question": "Which American band released 'Smells Like Teen Spirit'?", "answer": "nirvana"},
        {"question": "What song by Arijit Singh features the lyric 'Haan maine bhi pyar kiya'?", "answer": "kabhi jo baadal barse"},
        {"question": "What Australian band released 'Never Tear Us Apart'?", "answer": "inxs"},
        {"question": "Which Indian classical singer is known for khyal in Raag Hansadhwani?", "answer": "ustad rashid khan"},
        {"question": "What genre of music did Miriam Makeba popularize?", "answer": "south african"},
        {"question": "Who composed 'Messiah' with the famous Hallelujah Chorus?", "answer": "handel"},
        {"question": "What instrument is used in Australian Aboriginal music?", "answer": "didgeridoo"},
        {"question": "Which song by The Byrds features the lyric 'Eight miles high and when you touch down'?", "answer": "eight miles high"},
        {"question": "What Indian pop artist is known for 'Made in India'?", "answer": "alka yagnik"},
        {"question": "Which American artist sang 'Like a Rolling Stone'?", "answer": "bob dylan"},
        {"question": "What genre of music is associated with Indonesian gamelan?", "answer": "indonesian"},
        {"question": "Who sang 'Jogi' with a mix of bhangra and hip-hop?", "answer": "panjabi mc"},
        {"question": "What Korean pop group released 'Butter'?", "answer": "bts"},
        {"question": "Which Indian song features the lyric 'Aye mere watan ke logo'?", "answer": "aye mere watan ke logo"},
        {"question": "What instrument is central to Arabic music?", "answer": "oud"},
        {"question": "Which Australian artist sang 'Torn'?", "answer": "natalie imbruglia"},
        {"question": "What song by Shankar-Ehsaan-Loy features the lyric 'Dil chahta hai'?", "answer": "dil chahta hai"},
        {"question": "Who is the Indian composer behind 'Breathless'?", "answer": "shankar mahadevan"},
        {"question": "What genre of music did Osibisa release with 'Sunshine Day'?", "answer": "afro-rock"},
        {"question": "Which American artist sang 'I Will Always Love You'?", "answer": "whitney houston"},
        {"question": "What traditional Thai instrument is a bamboo mouth organ?", "answer": "khaen"},
        {"question": "Which song by Badshah features the lyric 'She move it like'?", "answer": "she move it like"},
        {"question": "Who composed 'Moonlight Sonata'?", "answer": "beethoven"},
        {"question": "What Native American song style uses vocables and is accessible to all tribes?", "answer": "aim song"},
        {"question": "Which Indian band is known for folk-fusion in 'Ma Rewa'?", "answer": "indian ocean"},
        {"question": "What Australian band released 'Beds Are Burning'?", "answer": "midnight oil"},
        {"question": "Which song by The Beatles features the lyric 'All you need is love'?", "answer": "all you need is love"},
        {"question": "What genre of music is associated with Persian poetry and melancholic sound?", "answer": "persian"},
        {"question": "Who sang 'Paper Planes' with South Asian influences?", "answer": "m.i.a."},
        {"question": "What instrument is central to Carnatic music performances?", "answer": "veena"},
        {"question": "Which American band released 'Hotel California'?", "answer": "eagles"},
        {"question": "What song by Arijit Singh features the lyric 'Channa mereya'?", "answer": "channa mereya"},
        {"question": "What Australian artist sang 'Elastic Heart'?", "answer": "sia"},
        {"question": "Which Indian singer collaborated with Coldplay on 'Hymn for the Weekend'?", "answer": "beyoncé"},
        {"question": "What genre of music did Tansen develop during the Mughal Empire?", "answer": "thumri"},
        {"question": "Who sang 'Sunshine Day' in 1976?", "answer": "osibisa"},
        {"question": "What traditional Korean instrument is a six-stringed zither?", "answer": "gayageum"},
        {"question": "Which song by Diljit Dosanjh features the lyric 'G.O.A.T. in the game'?", "answer": "g.o.a.t."},
        {"question": "What American artist sang 'Purple Rain'?", "answer": "prince"},
        {"question": "What Indian music style is known for its use in devotional bhajans?", "answer": "bhakti"},
        {"question": "Which Australian band released 'Sweet Disposition'?", "answer": "the temper trap"},
        {"question": "Which song by Anjan Dutta features the lyric 'Bela bose, bela bose'?", "answer": "bela bose"},
        {"question": "What genre of music did John McLaughlin fuse with Indian elements in Shakti?", "answer": "jazz"},
        {"question": "Who sang 'Toxic' with a Bollywood sample?", "answer": "britney spears"},
        {"question": "What Native American music style is associated with the Tohono O'odham?", "answer": "waila"},
        {"question": "Which Indian singer is known for 'Vande Mataram' with A.R. Rahman?", "answer": "lata mangeshkar"},
        {"question": "What Australian artist sang 'Stay With Me'?", "answer": "sam smith"},
        {"question": "Which song by The Raghu Dixit Project features the lyric 'Mysore se aayi'?", "answer": "mysore se aayi"},
        {"question": "What instrument is central to bhangra dance performances?", "answer": "dholak"},
        {"question": "Who sang 'Combination Pizza Hut and Taco Bell'?", "answer": "das racist"},
        {"question": "What genre of music is associated with South African township jive?", "answer": "kwela"},
        {"question": "Which Indian composer is known for 'Lagaan' soundtrack?", "answer": "a.r. rahman"},
        {"question": "What Australian band released 'Who Can It Be Now?'?", "answer": "men at work"},
        {"question": "Which song by Arijit Singh features the lyric 'Tera yaar hoon main'?", "answer": "tera yaar hoon main"},
        {"question": "What traditional Chinese instrument is a plucked zither?", "answer": "guzheng"},
        {"question": "Who sang 'Love You To' with Indian raga influences?", "answer": "the beatles"},
        {"question": "What genre of music did Bhimsen Joshi specialize in?", "answer": "khyal"},
        {"question": "Which American artist sang 'Billie Jean'?", "answer": "michael jackson"},
        {"question": "What Australian artist sang 'Riptide'?", "answer": "vance joy"},
        {"question": "Which song by Shankar Mahadevan features the lyric 'Koi kahe kehta rahe'?", "answer": "koi kahe"},
        {"question": "What instrument is used in Tuvan throat singing?", "answer": "voice"},
        {"question": "Who sang 'Indian Flute' with Timbaland?", "answer": "truth hurts"},
        {"question": "What genre of music is associated with Brazilian samba?", "answer": "samba"},
        {"question": "Which Indian band released 'Kandisa'?", "answer": "indian ocean"},
        {"question": "What Australian band released 'Am I Ever Gonna See Your Face Again'?", "answer": "the angels"},
        {"question": "Which song by Badshah features the lyric 'Tareefan teri kya kya karun'?", "answer": "tareefan"},
        {"question": "What traditional Indian instrument is a double-reed wind instrument?", "answer": "shehnai"},
        {"question": "Who sang 'Down' with Asian underground influences?", "answer": "jay sean"},
        {"question": "What genre of music is associated with Argentine tango?", "answer": "tango"},
        {"question": "Which Indian singer is known for 'Saathiya'?", "answer": "sonu nigam"},
        {"question": "What Australian artist sang 'Never Be Like You'?", "answer": "flume"},
        {"question": "Which song by A.R. Rahman features the lyric 'Yeh jo des hai tera'?", "answer": "yeh jo des hai tera"},
        {"question": "What traditional Japanese instrument is a bamboo flute?", "answer": "shakuhachi"},
        {"question": "Who sang 'The Inner Light' with Indian influences?", "answer": "the beatles"},
        {"question": "What genre of music did Tyagaraja compose for?", "answer": "carnatic"},
        {"question": "Which American band released 'Stairway to Heaven'?", "answer": "led zeppelin"},
        {"question": "What Australian band released 'Throw Your Arms Around Me'?", "answer": "hunters & collectors"},
        {"question": "Which song by Diljit Dosanjh features the lyric 'Born to shine'?", "answer": "born to shine"},
        {"question": "What instrument is central to Hindustani music performances?", "answer": "sarod"},
        {"question": "Who sang 'Jannat' with Harshdeep Kaur?", "answer": "ezu"},
        {"question": "What genre of music is associated with Cuban salsa?", "answer": "salsa"},
        {"question": "Which Indian singer is known for 'Kal Ho Naa Ho'?", "answer": "sonu nigam"},
        {"question": "What Australian artist sang 'Cheap Thrills'?", "answer": "sia"},
        {"question": "Which song by Arijit Singh features the lyric 'Ae dil hai mushkil'?", "answer": "ae dil hai mushkil"},
        {"question": "What traditional Korean instrument is a bowed zither?", "answer": "haegeum"},
        {"question": "Who sang 'Tomorrow Never Knows' with Indian influences?", "answer": "the beatles"},
        {"question": "What genre of music is associated with Andalusian flamenco?", "answer": "flamenco"},
        {"question": "Which Indian band released 'Ma Tujhe Salaam'?", "answer": "a.r. rahman"},
        {"question": "What Australian band released 'Khe Sanh'?", "answer": "cold chisel"},
        {"question": "Which song by Badshah features the lyric 'Main tera boyfriend'?", "answer": "main tera boyfriend"},
        {"question": "What traditional Indian instrument is a plucked lute?", "answer": "sitar"},
        {"question": "Who sang 'Why This Kolaveri Di' with Tamil influences?", "answer": "dhanush"},
        {"question": "What genre of music is associated with Jamaican ska?", "answer": "ska"},
        {"question": "Which Indian singer is known for 'Tum Se Hi'?", "answer": "mohit chauhan"},
        {"question": "What Australian artist sang 'Somebody’s Watching Me'?", "answer": "rockwell"},
        {"question": "Which song by A.R. Rahman features the lyric 'Chaiyya chaiyya'?", "answer": "chaiyya chaiyya"},
        {"question": "What traditional Chinese instrument is a hammered dulcimer?", "answer": "yangqin"},
        {"question": "Who sang 'Gee! The Jeep Jumps!' during WWII?", "answer": "kim loo sisters"},
        {"question": "What genre of music is associated with Indian folk-fusion?", "answer": "folk-fusion"},
        {"question": "Which Indian singer is known for 'Kun Faya Kun'?", "answer": "a.r. rahman"},
        {"question": "What Australian band released 'Eagle Rock'?", "answer": "daddy cool"},
        {"question": "Which song by Diljit Dosanjh features the lyric 'Patiala peg'?", "answer": "patiala peg"},
        {"question": "What traditional Indian instrument is a bowed string instrument?", "answer": "sarangi"},
        {"question": "Who sang 'Ku Li' with Asian American influences?", "answer": "dawen wang"},
        {"question": "What genre of music is associated with Russian balalaika?", "answer": "russian folk"},
        {"question": "Which Indian singer is known for 'Mitwa'?", "answer": "shafqat amanat ali"},
        {"question": "What Australian artist sang 'Ho Hey'?", "answer": "the lumineers"},
        {"question": "Which song by Arijit Singh features the lyric 'Hamdard, hamdard'?", "answer": "hamdard"},
        {"question": "What traditional Japanese instrument is a three-stringed lute?", "answer": "shamisen"},
        {"question": "Who sang 'Hole Hole Bushi' in early Japanese American communities?", "answer": "anonymous"},
        {"question": "What genre of music is associated with Hawaiian slack-key guitar?", "answer": "hawaiian"},
        {"question": "Which Indian singer is known for 'Tere Bina'?", "answer": "a.r. rahman"},
        {"question": "What Australian band released 'Tomorrow'?", "answer": "silverchair"},
        {"question": "Which song by Badshah features the lyric 'Buzz, buzz, buzz'?", "answer": "buzz"},
        {"question": "What traditional Indian instrument is a pair of hand drums?", "answer": "tabla"}
    ],




   
    "gaming": [
        {"question": "What company created Super Mario?", "answer": "nintendo"},
        {"question": "What is the main character's name in The Legend of Zelda?", "answer": "link"},
        {"question": "Which game features Master Chief?", "answer": "halo"},
        {"question": "What does 'RPG' stand for in gaming?", "answer": "role playing game"},
        {"question": "In which game do you catch Pokémon?", "answer": "pokemon"},
        {"question": "What color is Sonic the Hedgehog?", "answer": "blue"},
        {"question": "Which company created Minecraft?", "answer": "mojang"},
        {"question": "What is the maximum level in Pac-Man?", "answer": "256"},
        {"question": "Which console was released first: PlayStation or Xbox?", "answer": "playstation"},
        {"question": "What does 'FPS' stand for in gaming?", "answer": "first person shooter"},
        {"question": "Which game, developed by Krafton, popularized the battle royale genre in 2017?", "answer": "pubg: battlegrounds"},
        {"question": "What is the name of the shrinking play zone in PUBG: Battlegrounds?", "answer": "blue zone"},
        {"question": "Which Indian version of PUBG Mobile was relaunched after a ban in 2020?", "answer": "battlegrounds mobile india"},
        {"question": "Which game features a battle royale mode with building mechanics?", "answer": "fortnite"},
        {"question": "What company developed 'Call of Duty: Warzone'?", "answer": "activision"},
        {"question": "Which game features a battle royale mode called 'Blackout'?", "answer": "call of duty: black ops 4"},
        {"question": "What is the main setting of 'Grand Theft Auto V'?", "answer": "los santos"},
        {"question": "Which game, developed by Respawn Entertainment, introduced a ping system to battle royale?", "answer": "apex legends"},
        {"question": "Which mobile battle royale game has over 1 billion downloads globally?", "answer": "pubg mobile"},
        {"question": "Which game features a battle royale mode called 'Firestorm'?", "answer": "battlefield v"},
        {"question": "What is the primary currency in 'Call of Duty: Mobile'?", "answer": "cod points"},
        {"question": "Which game features a character named Bangalore in its battle royale mode?", "answer": "apex legends"},
        {"question": "Which game, inspired by PUBG, allows up to 120 players in a single match?", "answer": "rules of survival"},
        {"question": "Which battle royale game started as an April Fool’s joke in 2018?", "answer": "totally accurate battlegrounds"},
        {"question": "Which game features supernatural abilities in a Prague-based battle royale?", "answer": "vampire: the masquerade - bloodhunt"},
        {"question": "What is the name of the main character in 'Call of Duty: Modern Warfare' (2019)?", "answer": "captain price"},
        {"question": "Which game features a 5v5 tactical shooter mode with agents like Jett?", "answer": "valorant"},
        {"question": "Which mobile battle royale game is known for its low-poly graphics and fast matches?", "answer": "free fire"},
        {"question": "Which game features a battle royale mode with mounts like horses and raptors?", "answer": "realm royale"},
        {"question": "Which Indian game features a soldier in the Galwan Valley?", "answer": "faug"},
        {"question": "Which game, a precursor to PUBG, featured zombies in a battle royale mod for Arma 2?", "answer": "dayz"},
        {"question": "What is the name of the map introduced in PUBG’s Season 6?", "answer": "karakin"},
        {"question": "Which game features a battle royale mode with 3v3 and 5v5 MOBA elements?", "answer": "brawl stars"},
        {"question": "Which company developed 'Free Fire MAX', a competitor to PUBG Mobile?", "answer": "garena"},
        {"question": "Which game features the quote 'Winner winner, chicken dinner!'?", "answer": "pubg: battlegrounds"},
        {"question": "Which game features a character named Crypto in its battle royale mode?", "answer": "apex legends"},
        {"question": "What is the primary currency in 'Fortnite'?", "answer": "v-bucks"},
        {"question": "Which game features the character Lara Croft?", "answer": "tomb raider"},
        {"question": "What company developed 'The Witcher 3: Wild Hunt'?", "answer": "cd projekt red"},
        {"question": "Which game series includes the character Kratos?", "answer": "god of war"},
        {"question": "What does 'MMORPG' stand for in gaming?", "answer": "massively multiplayer online role playing game"},
        {"question": "Which game features the quote 'War. War never changes.'?", "answer": "fallout"},
        {"question": "What is the name of the princess in Super Mario games?", "answer": "peach"},
        {"question": "Which company created the Grand Theft Auto series?", "answer": "rockstar games"},
        {"question": "What is the main setting of 'Red Dead Redemption 2'?", "answer": "wild west"},
        {"question": "What is the name of the main character in 'Final Fantasy VII'?", "answer": "cloud strife"},
        {"question": "Which Japanese company developed 'Street Fighter'?", "answer": "capcom"},
        {"question": "What is the primary resource mined in Minecraft?", "answer": "ore"},
        {"question": "Which game features the character Aloy?", "answer": "horizon zero dawn"},
        {"question": "What does 'RTS' stand for in gaming?", "answer": "real time strategy"},
        {"question": "Which game series includes the character Nathan Drake?", "answer": "uncharted"},
        {"question": "What is the name of the main antagonist in 'The Legend of Zelda: Ocarina of Time'?", "answer": "ganondorf"},
        {"question": "Which company developed 'Overwatch'?", "answer": "blizzard entertainment"},
        {"question": "What is the name of the main character in 'Assassin’s Creed II'?", "answer": "ezio auditore"},
        {"question": "Which game features a blocky world where players build with pixels?", "answer": "minecraft"},
        {"question": "What is the name of the main antagonist in 'Portal'?", "answer": "glados"},
        {"question": "Which Indian game developer created 'Raji: An Ancient Epic'?", "answer": "nodding heads games"},
        {"question": "What is the main weapon of Samus Aran in the Metroid series?", "answer": "power suit"},
        {"question": "Which game features the quote 'Finish him!'?", "answer": "mortal kombat"},
        {"question": "What company developed 'Elden Ring'?", "answer": "fromsoftware"},
        {"question": "Which game series is set in the fictional continent of Tamriel?", "answer": "the elder scrolls"},
        {"question": "What is the name of the main character in 'Half-Life'?", "answer": "gordon freeman"},
        {"question": "Which Australian studio developed 'Fruit Ninja'?", "answer": "halfbrick studios"},
        {"question": "What is the primary currency in 'Animal Crossing'?", "answer": "bells"},
        {"question": "Which game features the character Ellie in a post-apocalyptic world?", "answer": "the last of us"},
        {"question": "What does 'BR' stand for in gaming?", "answer": "battle royale"},
        {"question": "Which game series includes the character Solid Snake?", "answer": "metal gear solid"},
        {"question": "What is the name of the main antagonist in 'Super Mario Bros.'?", "answer": "bowser"},
        {"question": "Which company developed 'Fortnite'?", "answer": "epic games"},
        {"question": "What is the name of the main character in 'Horizon Forbidden West'?", "answer": "aloy"},
        {"question": "Which Indian mobile game features a character named Shiva in a subway chase?", "answer": "temple run"},
        {"question": "What is the main setting of 'Cyberpunk 2077'?", "answer": "night city"},
        {"question": "Which game features the quote 'All your base are belong to us'?", "answer": "zero wing"},
        {"question": "What company created the 'FIFA' series?", "answer": "ea sports"},
        {"question": "Which game series is set in the world of Hyrule?", "answer": "the legend of zelda"},
        {"question": "What is the name of the main character in 'Red Dead Redemption 2'?", "answer": "arthur morgan"},
        {"question": "Which Japanese company developed 'Resident Evil'?", "answer": "capcom"},
        {"question": "What is the primary objective in 'Among Us'?", "answer": "complete tasks"},
        {"question": "Which game features a character named Tracer?", "answer": "overwatch"},
        {"question": "What does 'MOBA' stand for in gaming?", "answer": "multiplayer online battle arena"},
        {"question": "Which game series includes the character Joel Miller?", "answer": "the last of us"},
        {"question": "What is the name of the main antagonist in 'Final Fantasy XV'?", "answer": "ardyn izunia"},
        {"question": "Which Australian studio developed 'Crossy Road'?", "answer": "hipster whale"},
        {"question": "What is the main currency in 'Roblox'?", "answer": "robux"},
        {"question": "Which game features the character Leon S. Kennedy?", "answer": "resident evil"},
        {"question": "What is the name of the main character in 'Shadow of the Colossus'?", "answer": "wander"},
        {"question": "Which company developed 'League of Legends'?", "answer": "riot games"},
        {"question": "What is the main setting of 'The Witcher 3: Wild Hunt'?", "answer": "the continent"},
        {"question": "Which Indian game studio developed 'Asura: Tale of the Vanquished'?", "answer": "ogre head studio"},
        {"question": "What is the name of the main character in 'Bloodborne'?", "answer": "hunter"},
        {"question": "Which game features the quote 'It’s dangerous to go alone! Take this.'?", "answer": "the legend of zelda"},
        {"question": "What company developed 'Dark Souls'?", "answer": "fromsoftware"},
        {"question": "Which game series includes the character Commander Shepard?", "answer": "mass effect"},
        {"question": "What is the name of the main antagonist in 'Portal 2'?", "answer": "wheatley"},
        {"question": "Which Australian studio developed 'Hollow Knight'?", "answer": "team cherry"},
        {"question": "What is the primary weapon in 'Doom'?", "answer": "shotgun"},
        {"question": "Which game features a character named Bayonetta?", "answer": "bayonetta"},
        {"question": "What does 'VR' stand for in gaming?", "answer": "virtual reality"},
        {"question": "Which game series includes the character Sephiroth?", "answer": "final fantasy"},
        {"question": "What is the name of the main character in 'Ghost of Tsushima'?", "answer": "jin sakai"},
        {"question": "Which Indian game developer created 'Missing: Game for a Cause'?", "answer": "savant games"},
        {"question": "What is the main setting of 'Bioshock'?", "answer": "rapture"},
        {"question": "Which game features the quote 'The cake is a lie'?", "answer": "portal"},
        {"question": "What company developed 'StarCraft'?", "answer": "blizzard entertainment"},
        {"question": "Which game series is set in the world of Azeroth?", "answer": "world of warcraft"},
        {"question": "What is the name of the main character in 'Death Stranding'?", "answer": "sam porter bridges"},
        {"question": "Which Australian studio developed 'Jetpack Joyride'?", "answer": "halfbrick studios"},
        {"question": "What is the primary currency in 'Genshin Impact'?", "answer": "primogems"},
        {"question": "Which game features the character Geralt of Rivia?", "answer": "the witcher"},
        {"question": "What is the name of the main antagonist in 'Super Metroid'?", "answer": "mother brain"},
        {"question": "Which company developed 'Counter-Strike'?", "answer": "valve"},
        {"question": "Which game series includes the character Marcus Fenix?", "answer": "gears of war"},
        {"question": "What is the main setting of 'Assassin’s Creed Valhalla'?", "answer": "viking england"},
        {"question": "Which Indian game developer created 'Ludo King'?", "answer": "gametion technologies"},
        {"question": "What is the name of the main character in 'Sekiro: Shadows Die Twice'?", "answer": "wolf"},
        {"question": "Which game features the quote 'Do a barrel roll!'?", "answer": "star fox 64"},
        {"question": "What company developed 'Diablo'?", "answer": "blizzard entertainment"},
        {"question": "Which game series is set in the world of Midgar?", "answer": "final fantasy vii"},
        {"question": "What is the name of the main character in 'Control'?", "answer": "jesse faden"},
        {"question": "Which Australian studio developed 'Real Racing 3'?", "answer": "firemonkeys studios"},
        {"question": "What is the primary resource in 'Stardew Valley'?", "answer": "gold"},
        {"question": "Which game features the character Aerith Gainsborough?", "answer": "final fantasy vii"},
        {"question": "What is the name of the main antagonist in 'The Legend of Zelda: Breath of the Wild'?", "answer": "calamity ganon"},
        {"question": "Which company developed 'Destiny'?", "answer": "bungie"},
        {"question": "Which game series includes the character Sam Fisher?", "answer": "splinter cell"},
        {"question": "What is the main setting of 'Dishonored'?", "answer": "dunwall"},
        {"question": "Which Indian game studio developed 'Antariksha Sanchar'?", "answer": "quicksand gameslab"},
        {"question": "What is the name of the main character in 'Persona 5'?", "answer": "joker"},
        {"question": "Which game features the quote 'Praise the Sun!'?", "answer": "dark souls"},
        {"question": "What company developed 'Battlefield'?", "answer": "dice"},
        {"question": "Which game series is set in the world of Raccoon City?", "answer": "resident evil"},
        {"question": "What is the name of the main character in 'NieR: Automata'?", "answer": "2b"},
        {"question": "Which Australian studio developed 'Monument Valley'?", "answer": "ustwo games"},
        {"question": "What is the primary currency in 'Apex Legends'?", "answer": "apex coins"},
        {"question": "Which game features the character Clementine?", "answer": "the walking dead"},
        {"question": "What is the name of the main antagonist in 'Kingdom Hearts'?", "answer": "xehanort"},
        {"question": "Which company developed 'Team Fortress 2'?", "answer": "valve"},
        {"question": "Which game series includes the character Booker DeWitt?", "answer": "bioshock infinite"},
        {"question": "What is the main setting of 'Horizon Zero Dawn'?", "answer": "post-apocalyptic earth"},
        {"question": "Which Indian game developer created 'The Bonfire: Forsaken Lands'?", "answer": "xigma games"},
        {"question": "What is the name of the main character in 'Sly Cooper'?", "answer": "sly cooper"},
        {"question": "Which game features the quote 'Would you kindly?'?", "answer": "bioshock"},
        {"question": "What company developed 'Rocket League'?", "answer": "psyonix"},
        {"question": "Which game series is set in the world of Thedas?", "answer": "dragon age"},
        {"question": "What is the name of the main character in 'Hollow Knight'?", "answer": "knight"},
        {"question": "Which Australian studio developed 'The Gardens Between'?", "answer": "the voxel agents"},
        {"question": "What is the primary resource in 'No Man’s Sky'?", "answer": "units"},
        {"question": "Which game features the character Tifa Lockhart?", "answer": "final fantasy vii"},
        {"question": "What is the name of the main antagonist in 'God of War' (2018)?", "answer": "baldur"},
        {"question": "Which company developed 'Hearthstone'?", "answer": "blizzard entertainment"},
        {"question": "Which game series includes the character Ezio Auditore?", "answer": "assassin’s creed"},
        {"question": "What is the main setting of 'Fallout 4'?", "answer": "commonwealth"},
        {"question": "Which Indian game studio developed 'Rogue Heist'?", "answer": "lifelike studios"},
        {"question": "What is the name of the main character in 'Celeste'?", "answer": "madeline"},
        {"question": "Which game features the quote 'I used to be an adventurer like you, then I took an arrow in the knee'?", "answer": "the elder scrolls v: skyrim"},
        {"question": "What company developed 'Tetris'?", "answer": "alexey pajitnov"},
        {"question": "Which game series is set in the world of Yharnam?", "answer": "bloodborne"},
        {"question": "What is the primary currency in 'Valorant'?", "answer": "valorant points"},
        {"question": "Which game features the character Noctis Lucis Caelum?", "answer": "final fantasy xv"},
        {"question": "What is the name of the main antagonist in 'Super Mario 64'?", "answer": "bowser"},
        {"question": "Which company developed 'Dota 2'?", "answer": "valve"},
        {"question": "Which game series includes the character Max Payne?", "answer": "max payne"},
        {"question": "What is the main setting of 'Ghost of Tsushima'?", "answer": "tsushima island"},
        {"question": "Which Indian game developer created 'Real Cricket'?", "answer": "nautilus mobile"},
        {"question": "What is the name of the main character in 'Ori and the Blind Forest'?", "answer": "ori"},
        {"question": "Which game features the quote 'Kept you waiting, huh?'?", "answer": "metal gear solid"},
        {"question": "What company developed 'Need for Speed'?", "answer": "ea games"},
        {"question": "Which game series is set in the world of Ferelden?", "answer": "dragon age"},
        {"question": "Which Australian studio developed 'Hand of Fate'?", "answer": "defiant development"},
        {"question": "What is the primary resource in 'Terraria'?", "answer": "mana"},
        {"question": "Which game features the character Chloe Frazer?", "answer": "uncharted"},
        {"question": "What is the name of the main antagonist in 'Resident Evil 4'?", "answer": "ramon salazar"},
        {"question": "Which company developed 'Smite'?", "answer": "hi-rez studios"},
        {"question": "Which game series includes the character John Marston?", "answer": "red dead redemption"},
        {"question": "What is the main setting of 'Sekiro: Shadows Die Twice'?", "answer": "sengoku japan"},
        {"question": "Which Indian game studio developed 'Hitwicket Superstars'?", "answer": "hitwicket studios"},
        {"question": "What is the name of the main character in 'Firewatch'?", "answer": "henry"},
        {"question": "Which game features the quote 'What is a man? A miserable little pile of secrets!'?", "answer": "castlevania: aria of sorrow"},
        {"question": "What company developed 'Madden NFL'?", "answer": "ea sports"},
        {"question": "Which game series is set in the world of Columbia?", "answer": "bioshock infinite"},
        {"question": "What is the name of the main character in 'Cuphead'?", "answer": "cuphead"},
        {"question": "Which Australian studio developed 'Flight Control'?", "answer": "firemint"},
        {"question": "Which game features the character Ciri?", "answer": "the witcher 3: wild hunt"},
        {"question": "What is the name of the main antagonist in 'Metroid Prime'?", "answer": "metroid prime"},
        {"question": "Which company developed 'World of Tanks'?", "answer": "wargaming"},
        {"question": "Which game series includes the character Dante?", "answer": "devil may cry"},
        {"question": "What is the main setting of 'Control'?", "answer": "oldest house"},
        {"question": "Which game features a battle royale mode with a focus on realistic gunplay and no building?", "answer": "pubg: battlegrounds"},
        {"question": "Which game features a character named Wraith in its battle royale mode?", "answer": "apex legends"},
        {"question": "Which game series includes the character Trevor Philips?", "answer": "grand theft auto v"},
        {"question": "What is the name of the map in 'Call of Duty: Warzone' inspired by Verdansk?", "answer": "verdansk"},
        {"question": "Which game features a 5v5 bomb defusal mode with agents like Phoenix?", "answer": "valorant"},
        {"question": "Which Indian game developer created 'World Cricket Championship'?", "answer": "nextwave multimedia"},
        {"question": "Which game features a battle royale mode with a shrinking storm circle?", "answer": "fortnite"},
        {"question": "What is the name of the main antagonist in 'Call of Duty: Black Ops'?", "answer": "nikita dragovich"},
        {"question": "Which game features a character named Ajay Ghale?", "answer": "far cry 4"},
        {"question": "Which company developed 'Rainbow Six Siege'?", "answer": "ubisoft"},
        {"question": "What is the main setting of 'Call of Duty: Modern Warfare' (2019)?", "answer": "middle east"},
        {"question": "Which game features a battle royale mode with a focus on vehicular combat?", "answer": "grand theft auto v"},
        {"question": "Which Indian game studio developed 'Teen Patti Gold'?", "answer": "moonfrog labs"},
        {"question": "What is the name of the main character in 'Far Cry 3'?", "answer": "jason brody"},
        {"question": "Which game features the quote 'Drop, shock, and lock!'?", "answer": "call of duty: warzone"},
        {"question": "Which company developed 'Overwatch 2'?", "answer": "blizzard entertainment"},
        {"question": "Which game series is set in the world of San Andreas?", "answer": "grand theft auto"},
        {"question": "What is the name of the main character in 'Apex Legends' who uses a drone?", "answer": "crypto"}
    ],




  
    "funny": [
        {"question": "What do you call a sleeping bull?", "answer": "bulldozer"},
        {"question": "Why don't scientists trust atoms?", "answer": "because they make up everything"},
        {"question": "What do you call a bear with no teeth?", "answer": "gummy bear"},
        {"question": "Why don't eggs tell jokes?", "answer": "they would crack up"},
        {"question": "What do you call a fake noodle?", "answer": "impasta"},
        {"question": "How many tickles does it take to make an octopus laugh?", "answer": "tentacles"},
        {"question": "What do you call a dinosaur that crashes his car?", "answer": "tyrannosaurus wrecks"},
        {"question": "Why can't a bicycle stand up by itself?", "answer": "it's two tired"},
        {"question": "What do you call a fish wearing a bowtie?", "answer": "sofishticated"},
        {"question": "Why don't skeletons fight each other?", "answer": "they don't have the guts"},
        {"question": "What do you call a cow with no legs?", "answer": "ground beef"},
        {"question": "Why did the tomato turn red?", "answer": "it saw the salad dressing"},
        {"question": "What do you call a lazy kangaroo?", "answer": "pouch potato"},
        {"question": "Why don't programmers prefer dark mode?", "answer": "the light attracts bugs"},
        {"question": "Why was the math book sad?", "answer": "it had too many problems"},
        {"question": "What do you call a dog that does magic tricks?", "answer": "a labracadabrador"},
        {"question": "Why can't basketball players go on vacation?", "answer": "they would get called for traveling"},
        {"question": "What do you call a snake that works for the government?", "answer": "a civil serpent"},
        {"question": "Why did the scarecrow become a motivational speaker?", "answer": "he was outstanding in his field"},
        {"question": "What do you call a chai that tells bad jokes?", "answer": "deCAF"},
        {"question": "Why did the chicken join a band?", "answer": "it had the drumsticks"},
        {"question": "What do you call a potato that sings?", "answer": "a yamaha"},
        {"question": "Why don’t Indians play Uno?", "answer": "they’d eat the wild card"},
        {"question": "What do you call a sheep with no wool?", "answer": "a baa-ffle"},
        {"question": "Why did the computer go to art school?", "answer": "it wanted to draw a better byte"},
        {"question": "What do you call a Bollywood movie with no dance?", "answer": "a naach-neeto"},
        {"question": "Why don’t Australians play hide and seek?", "answer": "their animals are too good at it"},
        {"question": "What do you call a cat that loves video games?", "answer": "a purr-layer"},
        {"question": "Why did the banana go to the doctor?", "answer": "it wasn’t peeling well"},
        {"question": "What do you call a turtle that takes up photography?", "answer": "a snapper"},
        {"question": "Why don’t programmers trust stairs?", "answer": "they prefer the elevator"},
        {"question": "What do you call a pizza that tells jokes?", "answer": "a cheesy comedian"},
        {"question": "Why did the cricket ball go to school?", "answer": "it wanted to be a bouncer"},
        {"question": "What do you call a robot that loves to dance?", "answer": "a boogie bot"},
        {"question": "Why don’t elephants forget jokes?", "answer": "they have a trunk full of them"},
        {"question": "What do you call a spicy Indian dish that tells puns?", "answer": "a tikka talker"},
        {"question": "Why did the orange stop rolling?", "answer": "it ran out of juice"},
        {"question": "What do you call a ghost that haunts gamers?", "answer": "a boo-t camper"},
        {"question": "Why don’t some fruits make good singers?", "answer": "they’re always out of tune"},
        {"question": "What do you call a kangaroo that loves cricket?", "answer": "a bouncy bowler"},
        {"question": "Why did the bread go to therapy?", "answer": "it had too many kneady issues"},
        {"question": "What do you call a robot that loves curry?", "answer": "a tikka-tron"},
        {"question": "Why don’t owls tell jokes at night?", "answer": "they’d wake everyone up"},
        {"question": "What do you call a camel with no humps?", "answer": "a flatback"},
        {"question": "Why did the smartphone go to jail?", "answer": "it couldn’t stop breaking the law"},
        {"question": "What do you call a Pokémon that tells bad jokes?", "answer": "a pikachu-pun"},
        {"question": "Why don’t cows play chess?", "answer": "they’re afraid of any mooo-ve"},
        {"question": "What do you call a bear that loves dance music?", "answer": "a bhangra bear"},
        {"question": "Why did the pencil go to school?", "answer": "it wanted to be sharp"},
        {"question": "What do you call a frog that loves to game?", "answer": "a hopper-player"},
        {"question": "Why don’t some clocks tell jokes?", "answer": "they’re too ticked off"},
        {"question": "What do you call a lion that tells dad jokes?", "answer": "a roar-some comedian"},
        {"question": "Why did the samosa go to a comedy club?", "answer": "it wanted to spice things up"},
        {"question": "What do you call a tree that loves to code?", "answer": "a branch programmer"},
        {"question": "Why don’t sharks tell jokes?", "answer": "they’re too jaws-some"},
        {"question": "What do you call a parrot that plays PUBG?", "answer": "a squawk-dropping pro"},
        {"question": "Why did the mango go to a party?", "answer": "it was ripe for fun"},
        {"question": "What do you call a rabbit that plays Fortnite?", "answer": "a bunny battler"},
        {"question": "Why don’t lemons tell secrets?", "answer": "they’d spill the juice"},
        {"question": "What do you call a cow that loves Call of Duty?", "answer": "a mooo-t shooter"},
        {"question": "Why did the clock go to therapy?", "answer": "it had too many second thoughts"},
        {"question": "What do you call a snake that plays Valorant?", "answer": "a viper pro"},
        {"question": "Why don’t some flowers tell jokes?", "answer": "they’d wilt under pressure"},
        {"question": "What do you call a chicken that loves GTA?", "answer": "a cluck criminal"},
        {"question": "Why did the cucumber blush at the vegetable party?", "answer": "it overheard a steamy stew joke"},
        {"question": "What do you call a dog that loves Minecraft?", "answer": "a bark builder"},
        {"question": "Why don’t giraffes tell short jokes?", "answer": "they prefer long ones"},
        {"question": "What do you call a panda that loves to rap?", "answer": "a bamboozler"},
        {"question": "Why did the tea go to a comedy show?", "answer": "it wanted to steep up the laughs"},
        {"question": "What do you call a monkey that plays Among Us?", "answer": "a sneaky simian"},
        {"question": "Why don’t some stars tell jokes?", "answer": "they’re too bright for it"},
        {"question": "What do you call a horse that loves music?", "answer": "a galloping ghazal"},
        {"question": "Why did the apple go to school?", "answer": "it wanted to be a core subject"},
        {"question": "What do you call a penguin that plays Rocket League?", "answer": "a sliding scorer"},
        {"question": "Why don’t bees tell secrets?", "answer": "they’d buzz about it"},
        {"question": "What do you call a tiger that loves to code?", "answer": "a roaring coder"},
        {"question": "Why did the dosa go to a comedy club?", "answer": "it wanted to flip the crowd"},
        {"question": "What do you call a wolf that plays Overwatch?", "answer": "a howling hero"},
        {"question": "Why don’t clouds tell jokes?", "answer": "they’d rain on the punchline"},
        {"question": "What do you call a goat that loves GTA V?", "answer": "a bleating bandit"},
        {"question": "Why did the onion go to therapy?", "answer": "it had too many layers of issues"},
        {"question": "What do you call a koala that plays Apex Legends?", "answer": "a eucalyptus eliminator"},
        {"question": "Why don’t some books tell jokes?", "answer": "they’re too bound up"},
        {"question": "What do you call a camel that loves movies?", "answer": "a humpy hero"},
        {"question": "Why did the carrot go to a comedy show?", "answer": "it wanted to be a little more appealing"},
        {"question": "What do you call a bear that plays Free Fire?", "answer": "a grizzly gunner"},
        {"question": "Why don’t some rivers tell jokes?", "answer": "they just flow past the punchline"},
        {"question": "What do you call a sheep that loves Pokémon?", "answer": "a woolly trainer"},
        {"question": "Why did the coffee go to school?", "answer": "it wanted to brew some knowledge"},
        {"question": "What do you call a fox that plays Valorant?", "answer": "a cunning camper"},
        {"question": "Why don’t some mountains tell jokes?", "answer": "they’re too rocky for humor"},
        {"question": "What do you call a pig that loves Call of Duty?", "answer": "a bacon blaster"},
        {"question": "Why did the idli go to a comedy club?", "answer": "it wanted to steam up the laughs"},
        {"question": "What do you call a dolphin that plays Fortnite?", "answer": "a flipper fighter"},
        {"question": "Why don’t some trees tell jokes?", "answer": "they’re too wooden"},
        {"question": "What do you call a cow that loves music?", "answer": "a moosical maestro"},
        {"question": "Why did the grape go to a party?", "answer": "it wanted to get crushed"},
        {"question": "What do you call a lion that plays PUBG?", "answer": "a roaring royale"},
        {"question": "Why don’t some lamps tell jokes?", "answer": "they’re too dim"},
        {"question": "What do you call a kangaroo that loves Minecraft?", "answer": "a hopping crafter"},
        {"question": "Why did the butter go to therapy?", "answer": "it kept getting spread too thin"},
        {"question": "What do you call a parrot that plays Among Us?", "answer": "a squawking saboteur"},
        {"question": "Why don’t some doors tell jokes?", "answer": "they’re too closed off"},
        {"question": "What do you call a tiger that loves dance?", "answer": "a bhangra beast"},
        {"question": "Why did the peach go to school?", "answer": "it wanted to be a little juicier"},
        {"question": "What do you call a wolf that plays Rocket League?", "answer": "a howling striker"},
        {"question": "Why don’t some hats tell jokes?", "answer": "they’re too capped"},
        {"question": "What do you call a horse that plays GTA?", "answer": "a neigh-sance criminal"},
        {"question": "Why did the vada go to a comedy club?", "answer": "it wanted to fry the audience"},
        {"question": "What do you call a bear that plays Overwatch?", "answer": "a furry flanker"},
        {"question": "Why don’t some oceans tell jokes?", "answer": "they’re too deep"},
        {"question": "What do you call a goat that loves Pokémon?", "answer": "a bleating battler"},
        {"question": "Why did the corn go to therapy?", "answer": "it had too many kernel issues"},
        {"question": "What do you call a koala that plays Free Fire?", "answer": "a cuddly camper"},
        {"question": "Why don’t some walls tell jokes?", "answer": "they’re too bricked up"},
        {"question": "What do you call a camel that loves cricket?", "answer": "a humpy hitter"},
        {"question": "Why did the pineapple go to a party?", "answer": "it wanted to be a little sweeter"},
        {"question": "What do you call a fox that plays Apex Legends?", "answer": "a sly sniper"},
        {"question": "Why don’t some bridges tell jokes?", "answer": "they’re too spanned out"},
        {"question": "What do you call a pig that loves Call of Duty?", "answer": "a hog of war"},
        {"question": "Why did the paneer go to a comedy club?", "answer": "it wanted to curdle the crowd"},
        {"question": "What do you call a dolphin that plays Valorant?", "answer": "a sonar shooter"},
        {"question": "Why don’t some lakes tell jokes?", "answer": "they’re too wet"},
        {"question": "What do you call a sheep that loves GTA?", "answer": "a woolly wanderer"},
        {"question": "Why did the broccoli go to therapy?", "answer": "it had too many steamed emotions"},
        {"question": "What do you call a lion that plays Fortnite?", "answer": "a roaring raider"},
        {"question": "Why don’t some chairs tell jokes?", "answer": "they’re too seated"},
        {"question": "What do you call a cow that loves films?", "answer": "a moovie star"},
        {"question": "Why did the strawberry go to school?", "answer": "it wanted to be a berry good student"},
        {"question": "What do you call a wolf that plays Minecraft?", "answer": "a crafting canine"},
        {"question": "Why don’t some clouds tell jokes?", "answer": "they’re too misty"},
        {"question": "What do you call a parrot that loves spicy food?", "answer": "a masala mawker"},
        {"question": "Why did the lemon go to a comedy show?", "answer": "it wanted to zest up the laughs"},
        {"question": "What do you call a dog that plays PUBG?", "answer": "a barking battler"},
        {"question": "Why don’t some stars tell jokes?", "answer": "they’re too twinkly"},
        {"question": "What do you call a kangaroo that loves music?", "answer": "a hopping harmonist"},
        {"question": "Why did the potato go to a party?", "answer": "it wanted to be a little mashier"},
        {"question": "What do you call a snake that loves Fortnite?", "answer": "a slithering stormer"},
        {"question": "Why don’t some rivers tell jokes?", "answer": "they’re too current"},
        {"question": "What do you call a bear that loves Call of Duty?", "answer": "a grizzly gunner"},
        {"question": "Why did the tomato go to therapy?", "answer": "it had too many saucy issues"},
        {"question": "What do you call a koala that plays GTA?", "answer": "a eucalyptus escapee"},
        {"question": "Why don’t some lamps tell jokes?", "answer": "they’re too shady"},
        {"question": "What do you call a camel that plays Valorant?", "answer": "a humpy hitman"},
        {"question": "Why did the mango go to school?", "answer": "it wanted to be a juicy scholar"},
        {"question": "What do you call a fox that plays Among Us?", "answer": "a sneaky saboteur"},
        {"question": "Why don’t some doors tell jokes?", "answer": "they’re too hinged"},
        {"question": "What do you call a tiger that loves cricket?", "answer": "a roaring run-scorer"},
        {"question": "Why did the cucumber go to a comedy club?", "answer": "it wanted to pickle the audience"},
        {"question": "What do you call a wolf that plays Free Fire?", "answer": "a howling hunter"},
        {"question": "Why don’t some mountains tell jokes?", "answer": "they’re too peaky"},
        {"question": "What do you call a pig that plays Rocket League?", "answer": "a porky pusher"},
        {"question": "Why did the samosa go to therapy?", "answer": "it was stuffed with issues"},
        {"question": "What do you call a dolphin that loves Pokémon?", "answer": "a fin-tastic trainer"},
        {"question": "Why don’t some trees tell jokes?", "answer": "they’re too sappy"},
        {"question": "What do you call a cow that plays Overwatch?", "answer": "a mooo-ving tank"},
        {"question": "Why did the orange go to a party?", "answer": "it wanted to zest up the vibe"},
        {"question": "What do you call a lion that loves Apex Legends?", "answer": "a pride predator"},
        {"question": "Why don’t some chairs tell jokes?", "answer": "they’re too rigid"},
        {"question": "What do you call a kangaroo that loves dance?", "answer": "a bhangra bouncer"},
        {"question": "Why did the carrot go to school?", "answer": "it wanted to be a crisp learner"},
        {"question": "What do you call a bear that plays Minecraft?", "answer": "a blocky bruin"},
        {"question": "Why don’t some clouds tell jokes?", "answer": "they’re too foggy"},
        {"question": "What do you call a parrot that plays Call of Duty?", "answer": "a feathered fragger"},
        {"question": "Why did the apple go to a comedy show?", "answer": "it wanted to core the crowd"},
        {"question": "What do you call a snake that loves PUBG?", "answer": "a coil camper"},
        {"question": "Why don’t some lamps tell jokes?", "answer": "they’re too lit"},
        {"question": "What do you call a koala that plays Fortnite?", "answer": "a leafy looter"},
        {"question": "Why did the paneer go to school?", "answer": "it wanted to be a cheesy scholar"},
        {"question": "What do you call a fox that loves GTA?", "answer": "a foxy felon"},
        {"question": "Why don’t some rivers tell jokes?", "answer": "they’re too stream-lined"},
        {"question": "What do you call a sheep that plays Valorant?", "answer": "a woolly warrior"},
        {"question": "Why did the broccoli go to a party?", "answer": "it wanted to branch out"},
        {"question": "What do you call a lion that plays Among Us?", "answer": "a sneaky stalker"},
        {"question": "Why don’t some mountains tell jokes?", "answer": "they’re too steep"},
        {"question": "What do you call a pig that loves Pokémon?", "answer": "a porky trainer"},
        {"question": "Why did the idli go to therapy?", "answer": "it was too steamed up"},
        {"question": "What do you call a dolphin that plays Rocket League?", "answer": "a flipper forward"},
        {"question": "Why don’t some trees tell jokes?", "answer": "they’re too leafy"},
        {"question": "What do you call a cow that plays Free Fire?", "answer": "a bovine blaster"},
        {"question": "Why did the grape go to school?", "answer": "it wanted to be a wine scholar"},
        {"question": "What do you call a kangaroo that plays Overwatch?", "answer": "a hopping healer"},
        {"question": "Why don’t some clouds tell jokes?", "answer": "they’re too stormy"},
        {"question": "What do you call a bear that loves cricket?", "answer": "a grizzly googly"},
        {"question": "Why did the tomato go to a comedy club?", "answer": "it wanted to ketchup with laughs"},
        {"question": "What do you call a wolf that plays Apex Legends?", "answer": "a pack predator"},
        {"question": "Why don’t some lamps tell jokes?", "answer": "they’re too flickery"},
        {"question": "What do you call a parrot that loves GTA?", "answer": "a plumage pilferer"}
    ],

    
    "science": [
    {"question": "What is the chemical symbol for water?", "answer": "H2O"},
    {"question": "What planet is known as the Red Planet?", "answer": "Mars"},
    {"question": "What is the primary source of energy for Earth's climate?", "answer": "Sun"},
    {"question": "What gas makes up about 78% of Earth's atmosphere?", "answer": "Nitrogen"},
    {"question": "What is the boiling point of water in Celsius?", "answer": "100"},
    {"question": "What is the SI unit of force?", "answer": "Newton"},
    {"question": "Which element has the atomic number 6?", "answer": "Carbon"},
    {"question": "What is the process by which plants make their food?", "answer": "Photosynthesis"},
    {"question": "What is the nearest star to Earth besides the Sun?", "answer": "Proxima Centauri"},
    {"question": "What type of energy is stored in a stretched spring?", "answer": "Potential"}
  ],



  "art_design": [
    {"question": "Who painted the Mona Lisa?", "answer": "Leonardo da Vinci"},
    {"question": "What art movement is associated with Picasso's 'Guernica'?", "answer": "Cubism"},
    {"question": "What is the primary color that, when mixed with blue, makes purple?", "answer": "Red"},
    {"question": "What is the name of the famous sculpture by Michelangelo depicting a biblical hero?", "answer": "David"},
    {"question": "Which art style emphasizes light and its changing qualities?", "answer": "Impressionism"},
    {"question": "What material is commonly used in pottery?", "answer": "Clay"},
    {"question": "Who designed the iconic 'Fallingwater' house?", "answer": "Frank Lloyd Wright"},
    {"question": "What is the term for a painting done on wet plaster?", "answer": "Fresco"},
    {"question": "What art form involves arranging colored glass into patterns?", "answer": "Stained Glass"},
    {"question": "Which artist is known for large-scale soup can paintings?", "answer": "Andy Warhol"}
  ],


  "travel_adventure": [
    {"question": "What is the capital city of Brazil?", "answer": "Brasilia"},
    {"question": "Which country is home to the Great Barrier Reef?", "answer": "Australia"},
    {"question": "What is the tallest mountain in the world?", "answer": "Mount Everest"},
    {"question": "Which city is famous for its Leaning Tower?", "answer": "Pisa"},
    {"question": "What is the longest river in South America?", "answer": "Amazon"},
    {"question": "Which African country is known for its pyramids?", "answer": "Egypt"},
    {"question": "What is the name of the famous canyon in Arizona, USA?", "answer": "Grand Canyon"},
    {"question": "Which country is known as the Land of the Rising Sun?", "answer": "Japan"},
    {"question": "What is the smallest country in the world by land area?", "answer": "Vatican City"},
    {"question": "Which continent is home to the Sahara Desert?", "answer": "Africa"}
  ],


  "cooking_cuisine": [
    {"question": "What is the main ingredient in guacamole?", "answer": "Avocado"},
    {"question": "Which country is known for sushi?", "answer": "Japan"},
    {"question": "What is the primary grain used in risotto?", "answer": "Arborio Rice"},
    {"question": "What herb is commonly used in pesto sauce?", "answer": "Basil"},
    {"question": "What is the traditional French dish made with beef and red wine?", "answer": "Beef Bourguignon"},
    {"question": "Which spice gives curry its yellow color?", "answer": "Turmeric"},
    {"question": "What is the Italian dish consisting of thin layers of pasta, sauce, and cheese?", "answer": "Lasagna"},
    {"question": "What fruit is used to make traditional jam in France?", "answer": "Apricot"},
    {"question": "What is the main ingredient in hummus?", "answer": "Chickpeas"},
    {"question": "Which cuisine is known for its use of lemongrass and coconut milk?", "answer": "Thai"}
  ],



  "health_medicine": [
    {"question": "What is the largest organ in the human body?", "answer": "Skin"},
    {"question": "What vitamin is primarily obtained from sunlight?", "answer": "Vitamin D"},
    {"question": "What is the medical term for high blood pressure?", "answer": "Hypertension"},
    {"question": "Which organ filters blood and removes waste as urine?", "answer": "Kidney"},
    {"question": "What is the name of the protein that carries oxygen in blood?", "answer": "Hemoglobin"},
    {"question": "What is the medical term for a heart attack?", "answer": "Myocardial Infarction"},
    {"question": "Which bone is commonly called the collarbone?", "answer": "Clavicle"},
    {"question": "What is the primary source of energy for the human body?", "answer": "Carbohydrates"},
    {"question": "What is the condition caused by a lack of insulin?", "answer": "Diabetes"},
    {"question": "Which part of the brain controls balance and coordination?", "answer": "Cerebellum"}
  ],



"programming": [
  { "question": "What does HTML stand for?", "answer": "HyperText Markup Language" },
  { "question": "Which programming language uses indentation to define code blocks?", "answer": "Python" },
  { "question": "What does this output?\n\n```js\nconsole.log(typeof null);\n```", "answer": "object" },
  { "question": "What does CSS stand for?", "answer": "Cascading Style Sheets" },
  { "question": "Which symbol is used for comments in Python?", "answer": "#" },
  { "question": "What does the following print?\n\n```python\nprint(10 // 3)\n```", "answer": "3" },
  { "question": "What does this C++ code print?\n\n```cpp\nint x = 5;\ncout << x++;\n```", "answer": "5" },
  { "question": "What will this return?\n\n```sql\nSELECT MAX(score) FROM students;\n```", "answer": "Returns the highest score from 'students'" },
  { "question": "What is the output?\n\n```js\nconsole.log(2 + '2');\n```", "answer": "22" },
  { "question": "Which language is used to style websites?", "answer": "CSS" },
  { "question": "What is a loop used for?", "answer": "To repeat a block of code" },
  { "question": "What is the output?\n\n```python\nprint('Hello' * 2)\n```", "answer": "HelloHello" },
  { "question": "What is the purpose of `git clone`?", "answer": "To copy a repository locally" },
  { "question": "Which operator checks equality in JavaScript?", "answer": "===" },
  { "question": "What is SQL used for?", "answer": "Managing and querying databases" },
  { "question": "What does this Java code print?\n\n```java\nSystem.out.println(3 + 4 + \"5\");\n```", "answer": "75" },
  { "question": "Which tag is used for links in HTML?", "answer": "<a>" },
  { "question": "What is a function?", "answer": "A reusable block of code" },
  { "question": "What is the output?\n\n```js\nlet x = 5;\nx += 3;\nconsole.log(x);\n```", "answer": "8" },
  { "question": "What is the extension of a Python file?", "answer": ".py" },
  { "question": "Which keyword is used to define a class in Java?", "answer": "class" },
  { "question": "What does this return?\n\n```python\nlen(\"hello\")\n```", "answer": "5" },
  { "question": "What does this code print?\n\n```cpp\nint a = 10;\ncout << a * a;\n```", "answer": "100" },
  { "question": "Which function is used to get user input in Python?", "answer": "input()" },
  { "question": "What does this JavaScript function do?\n\n```js\nfunction greet() {\n  alert(\"Hello!\");\n}\n```", "answer": "Shows an alert with 'Hello!'" },
  { "question": "What is a variable?", "answer": "A named storage for data" },
  { "question": "Which SQL clause is used to filter rows?", "answer": "WHERE" },
  { "question": "What is the default port of HTTP?", "answer": "80" },
  { "question": "What does this do?\n\n```git\ngit init\n```", "answer": "Initializes a new Git repository" },
  { "question": "Which data type represents True/False?", "answer": "Boolean" },
  { "question": "What is the output?\n\n```python\nx = '7'\nprint(int(x) + 1)\n```", "answer": "8" },
  { "question": "Which CSS property changes text color?", "answer": "color" },
  { "question": "Which HTML element is used to display headings?", "answer": "<h1> to <h6>" },
  { "question": "What does the term 'frontend' refer to?", "answer": "The part of a web app users interact with" },
  { "question": "What is the output?\n\n```js\nconsole.log(4 ** 2);\n```", "answer": "16" },
  { "question": "Which keyword is used to import modules in Python?", "answer": "import" },
  { "question": "What does this do?\n\n```sql\nSELECT * FROM users;\n```", "answer": "Fetches all rows from the 'users' table" },
  { "question": "Which language is known for its use in AI/ML?", "answer": "Python" },
  { "question": "What is the purpose of a constructor in OOP?", "answer": "To initialize objects" },
  { "question": "What is the output?\n\n```python\nprint(bool(0))\n```", "answer": "False" },
  { "question": "Which tag inserts a line break in HTML?", "answer": "<br>" },
  { "question": "Which programming paradigm uses 'objects'?", "answer": "Object-Oriented Programming (OOP)" },
  { "question": "What does this C++ code do?\n\n```cpp\nint x = 1;\nwhile(x < 5) {\n  cout << x++;\n}\n```", "answer": "1234" },
  { "question": "What is the file extension of CSS files?", "answer": ".css" },
  { "question": "Which JavaScript method converts a string to an integer?", "answer": "parseInt()" },
  { "question": "What does SQL stand for?", "answer": "Structured Query Language" },
  { "question": "Which symbol is used for exponentiation in Python?", "answer": "**" },
  { "question": "What is the output?\n\n```python\nprint(9 % 2)\n```", "answer": "1" },
  { "question": "Which command stages files for commit in Git?", "answer": "git add" },
  { "question": "What is the output?\n\n```js\nconsole.log(true && false);\n```", "answer": "false" },
  { "question": "What is the purpose of 'return' in a function?", "answer": "To send a value back to the caller" },
  { "question": "What is the difference between == and === in JavaScript?", "answer": "== allows type conversion; === does not" },
  { "question": "What is the output?\n\n```java\nSystem.out.println(\"Hi \" + 2 + 3);\n```", "answer": "Hi 23" },
  { "question": "What does this Python code do?\n\n```python\nprint(2 < 5 < 10)\n```", "answer": "True" },
  { "question": "Which tag is used for unordered lists in HTML?", "answer": "<ul>" },
  { "question": "What does this command do?\n\n```git\ngit status\n```", "answer": "Shows the current status of the working directory" },
  { "question": "Which keyword is used to exit a loop in Python?", "answer": "break" },
  { "question": "What is the result of this?\n\n```sql\nSELECT AVG(score) FROM results;\n```", "answer": "Returns the average score" },
  { "question": "Which JavaScript method adds an element to an array?", "answer": "push()" }
],




  "photography": [
    {"question": "What does ISO measure in photography?", "answer": "Light Sensitivity"},
    {"question": "What is the term for the amount of light entering a camera lens?", "answer": "Aperture"},
    {"question": "Which camera brand is known for its EOS series?", "answer": "Canon"},
    {"question": "What is the technique for capturing a subject in motion with a blurred background?", "answer": "Panning"},
    {"question": "What does a high shutter speed help to achieve?", "answer": "Freeze Motion"},
    {"question": "What is the name of the scale used to measure aperture size?", "answer": "F-stop"},
    {"question": "Which type of lens is best for portrait photography?", "answer": "Prime"},
    {"question": "What is the term for the range of distance that appears sharp in a photo?", "answer": "Depth of Field"},
    {"question": "Which company is famous for its mirrorless Z-series cameras?", "answer": "Nikon"},
    {"question": "What does RAW refer to in digital photography?", "answer": "Unprocessed Image File"}
  ],


  "nature_wildlife": [
    {"question": "What is the largest land animal on Earth?", "answer": "African Elephant"},
    {"question": "Which bird is known for its inability to fly and lives in Antarctica?", "answer": "Penguin"},
    {"question": "What is the largest species of big cat?", "answer": "Tiger"},
    {"question": "Which plant is known for its ability to trap and digest insects?", "answer": "Venus Flytrap"},
    {"question": "What is the primary food source for a giant panda?", "answer": "Bamboo"},
    {"question": "Which ocean is home to the Great Barrier Reef?", "answer": "Pacific"},
    {"question": "What is the term for animals that are active at night?", "answer": "Nocturnal"},
    {"question": "Which animal is known as the 'ship of the desert'?", "answer": "Camel"},
    {"question": "What is the largest species of shark?", "answer": "Whale Shark"},
    {"question": "Which tree is known for its extremely long lifespan, up to thousands of years?", "answer": "Bristlecone Pine"}
  ]
}


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

@app.get("/api/categories")
async def get_categories():
    """Get all available categories with their question counts"""
    categories_info = {}
    for category, puzzles in CATEGORY_PUZZLES.items():
        categories_info[category] = {
            "name": category.replace("_", " ").title(),
            "count": len(puzzles)
        }
    return {"categories": categories_info}

@app.get("/api/puzzles/{category}")
async def get_puzzles_by_category(category: str):
    """Get puzzles for a specific category"""
    if category not in CATEGORY_PUZZLES:
        raise HTTPException(status_code=404, detail="Category not found")
    
    return {"category": category, "puzzles": CATEGORY_PUZZLES[category]}

@app.get("/api/puzzles")
async def get_puzzles():
    """Get all puzzles (backward compatibility)"""
    all_puzzles = []
    for category, puzzles in CATEGORY_PUZZLES.items():
        for puzzle in puzzles:
            puzzle_with_category = puzzle.copy()
            puzzle_with_category["category"] = category
            all_puzzles.append(puzzle_with_category)
    return {"puzzles": all_puzzles}

@app.get("/api/stats")
async def get_stats():
    try:
        total_users = await db.users.count_documents({})
        total_questions = sum(len(puzzles) for puzzles in CATEGORY_PUZZLES.values())
        return {
            "total_users": total_users,
            "active_games": len(active_games),
            "connected_players": len(connected_players),
            "waiting_players": len(waiting_players),
            "total_categories": len(CATEGORY_PUZZLES),
            "total_questions": total_questions
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
                    category = message.get("category", "general_knowledge")
                    await handle_matchmaking(username, websocket, category)
                elif message["type"] == "submit_answer":
                    await handle_answer(username, message.get("answer", ""), websocket)
                elif message["type"] == "cancel_search":
                    await handle_cancel_search(username, websocket)
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
    
    if username in waiting_players:
        del waiting_players[username]
        
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

async def handle_cancel_search(username: str, websocket: WebSocket):
    """Handle when player cancels matchmaking"""
    if username in waiting_players:
        del waiting_players[username]
        await websocket.send_text(json.dumps({
            "type": "search_cancelled",
            "message": "Matchmaking cancelled"
        }))

async def handle_matchmaking(username: str, websocket: WebSocket, category: str):
    """Handle matchmaking logic with category support"""
    if category not in CATEGORY_PUZZLES:
        await websocket.send_text(json.dumps({
            "type": "error",
            "message": "Invalid category selected"
        }))
        return
    
    # Look for existing waiting player in the same category
    waiting_opponent = None
    for waiting_username, waiting_info in waiting_players.items():
        if (waiting_info["category"] == category and 
            waiting_username != username and 
            waiting_username in connected_players):
            waiting_opponent = waiting_username
            break
    
    if waiting_opponent:
        # Match found! Create game
        game_id = f"game_{len(active_games) + 1}_{username}_{waiting_opponent}"
        
        # Remove from waiting
        del waiting_players[waiting_opponent]
        if username in waiting_players:
            del waiting_players[username]
        
        # Select random puzzle from category
        puzzle = random.choice(CATEGORY_PUZZLES[category])
        
        # Create game session
        active_games[game_id] = GameSession(
            players=[username, waiting_opponent],
            category=category,
            current_puzzle=puzzle
        )
        
        # Notify both players
        for player in [username, waiting_opponent]:
            if player in connected_players:
                try:
                    await connected_players[player].send_text(json.dumps({
                        "type": "game_start",
                        "game_id": game_id,
                        "category": category,
                        "puzzle": puzzle["question"],
                        "opponent": waiting_opponent if player == username else username
                    }))
                except Exception as e:
                    logger.error(f"Error starting game for {player}: {e}")
        
        logger.info(f"Game started: {game_id} with category {category}")
    else:
        # No match found, add to waiting
        waiting_players[username] = {
            "category": category,
            "timestamp": datetime.utcnow()
        }
        
        await websocket.send_text(json.dumps({
            "type": "waiting_for_opponent",
            "category": category,
            "message": f"Searching for opponent in {category.replace('_', ' ').title()}..."
        }))
        
        logger.info(f"Player {username} waiting for match in category {category}")

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
    correct_answer = user_game.current_puzzle["answer"]
    
    if answer.lower().strip() == correct_answer.lower():
        user_game.winner = username
        
        # Calculate points based on category difficulty
        points = get_points_for_category(user_game.category)
        
        # Update score in database
        try:
            await db.users.update_one(
                {"username": username},
                {"$inc": {"score": points}}
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
                        "points": points if is_winner else 0,
                        "category": user_game.category,
                        "message": f"You won! +{points} points" if is_winner else f"{username} won! (+{points} points)"
                    }))
                except Exception as e:
                    logger.error(f"Error sending game end message to {player}: {e}")
        
        # Clean up game
        del active_games[game_id]
        logger.info(f"Game ended: {game_id}, winner: {username}")
    else:
        await websocket.send_text(json.dumps({
            "type": "wrong_answer",
            "message": "Wrong answer! Try again.",
            "hint": f"The answer should be {len(correct_answer)} characters long"
        }))

def get_points_for_category(category: str) -> int:
    """Return points based on category difficulty"""
    difficulty_points = {
        "basic_math": 5,
        "word_games": 10,
        "movies": 15,
        "music": 15,
        "funny": 10,
        "general_knowledge": 10,
        "social_science": 10,
        "science":10,
        "riddles": 15,
        "gaming": 10,
        "Oral_math": 15,
        "nature_wildlife":10,
        "photography": 10,
        "health_medicine":10,
        "programming":10,
        "cooking_cuisine":10,
        "travel_adventure":5,
        "art_design": 5
    }
    return difficulty_points.get(category, 10)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)