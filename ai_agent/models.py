"""Data models and structures for AI agent"""

from pydantic import BaseModel
from typing import Optional, Dict, Any

class Message(BaseModel):
    content: str
    context: Optional[Dict[str, Any]] = None

class Conversation:
    def __init__(self):
        self.messages = []
        self.context = {}

    def add_message(self, role: str, content: str):
        self.messages.append({"role": role, "content": content})

    def get_messages(self):
        return self.messages

    def update_context(self, new_context: Dict[str, Any]):
        self.context.update(new_context)

# Character corrections and known ranks/titles
CHARACTER_CORRECTIONS = {
    'serafino': 'Commander Serafino',
    'doctor serafino': 'Commander Serafino',
    'ankos': 'Doctor Ankos',
    'sif': 'Commander Sif',
    'zhal': 'Commander Zhal',
    'blaine': 'Captain Blaine',
    'marcus blaine': 'Captain Marcus Blaine',
    'eren': 'Captain Sereya Eren',
    'sereya eren': 'Captain Sereya Eren',
    'tolena': 'Maeve Blaine',
    'dryellia': 'Cadet Dryellia',
    'zarina dryellia': 'Cadet Zarina Dryellia',
    'snow': 'Cadet Snow',
    'rigby': 'Cadet Rigby',
    'scarlett': 'Cadet Scarlett',
    'bethany scarlett': 'Cadet Bethany Scarlett',
    'antony': 'Cadet Antony',
    'finney': 'Cadet Finney',
    'schwarzweld': 'Cadet Hedwik Schwarzweld',
    'kodor': 'Cadet Kodor',
    'vrajen kodor': 'Cadet Vrajen Kodor',
    'tavi': 'Cadet Antony'
} 