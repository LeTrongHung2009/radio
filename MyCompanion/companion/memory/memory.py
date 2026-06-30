"""
Memory Manager - Long-term memory storage and retrieval
Lightweight JSON/SQLite hybrid for efficient fact storage
"""
import asyncio
import json
import logging
from typing import Optional, List, Dict, Any
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class ConversationTurn:
    """Single conversation turn"""
    timestamp: float
    user_message: str
    ai_response: str
    emotion: str
    context: str = ""


class MemoryManager:
    """
    Manages short-term and long-term memory
    
    Features:
    - Conversation history (recent turns)
    - Fact extraction and storage
    - Identity management
    - Lightweight storage (JSON + SQLite optional)
    """
    
    def __init__(self, config=None):
        self.config = config
        
        # Storage paths
        self.memory_dir = Path('memory_db')
        self.memory_dir.mkdir(exist_ok=True)
        
        self.facts_file = self.memory_dir / 'local_facts.json'
        self.identity_file = self.memory_dir / 'identity.json'
        self.sessions_file = self.memory_dir / 'sessions.json'
        
        # In-memory caches
        self.recent_turns: List[ConversationTurn] = []
        self.max_recent_turns = 100
        
        self.facts: List[Dict[str, Any]] = []
        self.identity: Dict[str, Any] = {}
        
        # Statistics
        self.turns_stored = 0
        self.facts_extracted = 0
        
        logger.info("Memory manager initialized")
    
    async def initialize(self):
        """Load existing memory from disk"""
        await self._load_facts()
        await self._load_identity()
        logger.info("Memory loaded from disk")
    
    async def _load_facts(self):
        """Load facts from file"""
        try:
            if self.facts_file.exists():
                with open(self.facts_file, 'r', encoding='utf-8') as f:
                    self.facts = json.load(f)
                logger.info(f"Loaded {len(self.facts)} facts")
        except Exception as e:
            logger.error(f"Failed to load facts: {e}")
            self.facts = []
    
    async def _load_identity(self):
        """Load identity from file"""
        try:
            if self.identity_file.exists():
                with open(self.identity_file, 'r', encoding='utf-8') as f:
                    self.identity = json.load(f)
                logger.info(f"Loaded identity: {self.identity.get('name', 'Unknown')}")
        except Exception as e:
            logger.error(f"Failed to load identity: {e}")
            self.identity = {}
    
    async def add_turn(
        self,
        user_message: str,
        ai_response: str,
        emotion: str,
        context: str = ""
    ):
        """Add conversation turn to recent history"""
        turn = ConversationTurn(
            timestamp=datetime.now().timestamp(),
            user_message=user_message,
            ai_response=ai_response,
            emotion=emotion,
            context=context
        )
        
        self.recent_turns.append(turn)
        self.turns_stored += 1
        
        # Trim if too long
        if len(self.recent_turns) > self.max_recent_turns:
            self.recent_turns = self.recent_turns[-self.max_recent_turns:]
        
        logger.debug(f"Stored turn #{self.turns_stored}")
    
    async def get_recent_turns(self, limit: int = 10) -> List[ConversationTurn]:
        """Get most recent conversation turns"""
        return self.recent_turns[-limit:]
    
    async def extract_facts(self, text: str):
        """
        Extract factual information from text
        
        Simple heuristic extraction (would use LLM in full version)
        """
        # Simple patterns for fact extraction
        fact_patterns = [
            "my name is",
            "i am",
            "i'm",
            "i live",
            "i work",
            "i like",
            "i love",
            "my favorite",
        ]
        
        text_lower = text.lower()
        
        for pattern in fact_patterns:
            if pattern in text_lower:
                # Extract sentence as fact
                sentences = text.split('.')
                for sentence in sentences:
                    if pattern in sentence.lower():
                        fact = {
                            'text': sentence.strip(),
                            'timestamp': datetime.now().timestamp(),
                            'confidence': 0.8,
                            'source': 'conversation'
                        }
                        
                        # Avoid duplicates
                        if not any(f['text'] == fact['text'] for f in self.facts):
                            self.facts.append(fact)
                            self.facts_extracted += 1
                            logger.info(f"Extracted fact: {fact['text'][:50]}...")
                            
                            # Save to disk
                            await self._save_facts()
    
    async def _save_facts(self):
        """Save facts to disk"""
        try:
            with open(self.facts_file, 'w', encoding='utf-8') as f:
                json.dump(self.facts, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save facts: {e}")
    
    async def add_fact(self, fact_text: str, confidence: float = 1.0):
        """Manually add a fact"""
        fact = {
            'text': fact_text,
            'timestamp': datetime.now().timestamp(),
            'confidence': confidence,
            'source': 'manual'
        }
        
        self.facts.append(fact)
        await self._save_facts()
        logger.info(f"Added fact: {fact_text}")
    
    async def update_identity(self, key: str, value: Any):
        """Update identity information"""
        self.identity[key] = value
        
        try:
            with open(self.identity_file, 'w', encoding='utf-8') as f:
                json.dump(self.identity, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Updated identity: {key} = {value}")
        except Exception as e:
            logger.error(f"Failed to update identity: {e}")
    
    async def log_interaction_quality(
        self,
        user_message: str,
        ai_response: str,
        reaction: str
    ):
        """Log interaction quality for learning"""
        # Would store for later analysis in full version
        logger.debug(f"Interaction quality: {reaction}")
    
    async def search_facts(self, query: str) -> List[Dict[str, Any]]:
        """Search facts by keyword"""
        query_lower = query.lower()
        matches = [
            fact for fact in self.facts
            if query_lower in fact['text'].lower()
        ]
        return matches
    
    async def clear_recent_history(self):
        """Clear recent conversation turns"""
        self.recent_turns.clear()
        logger.info("Recent history cleared")
    
    async def save(self):
        """Save all memory to disk"""
        await self._save_facts()
        
        # Save sessions
        try:
            sessions_data = {
                'total_turns': self.turns_stored,
                'last_session': datetime.now().isoformat(),
                'facts_count': len(self.facts)
            }
            with open(self.sessions_file, 'w', encoding='utf-8') as f:
                json.dump(sessions_data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save sessions: {e}")
        
        logger.info("Memory saved to disk")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics"""
        return {
            'recent_turns': len(self.recent_turns),
            'total_turns_stored': self.turns_stored,
            'facts_count': len(self.facts),
            'facts_extracted': self.facts_extracted,
            'identity_keys': list(self.identity.keys()),
            'max_recent_turns': self.max_recent_turns
        }


# Singleton instance
_memory_manager: Optional[MemoryManager] = None


def get_memory_manager() -> MemoryManager:
    """Get global memory manager"""
    global _memory_manager
    if _memory_manager is None:
        raise RuntimeError("Memory manager not initialized!")
    return _memory_manager
