"""
Identity Manager - Core Identity System for AI Companion

This module manages the companion's identity, including:
- Loading identity profiles from JSON
- Managing self-concept and canonical information
- Providing identity context to AI reasoning
- Handling identity updates through learning
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
from companion.utils.singleton import singletons

logger = logging.getLogger(__name__)


class IdentityManager:
    """
    Manages the AI companion's core identity and self-concept.
    
    Responsibilities:
    - Load and validate identity profiles
    - Provide identity context for decision-making
    - Track identity evolution through experiences
    - Maintain consistency with canonical character data
    """
    
    def __init__(self, identity_path: str = None):
        """
        Initialize Identity Manager
        
        Args:
            identity_path: Path to identity JSON file
        """
        self.identity_path = identity_path or "./companion/identity/miku_profile.json"
        self.identity_data: Dict[str, Any] = {}
        self.canonical_data: Dict[str, Any] = {}
        self.personality_core: Dict[str, Any] = {}
        self.knowledge_base: Dict[str, Any] = {}
        self.ethical_guidelines: Dict[str, Any] = {}
        
        # Dynamic identity aspects (can evolve)
        self.user_relationship: Dict[str, Any] = {
            "interaction_count": 0,
            "first_meeting": None,
            "last_interaction": None,
            "shared_memories": [],
            "inside_jokes": [],
            "user_preferences_learned": {},
            "trust_level": 0.5,  # 0.0 to 1.0
            "intimacy_depth": 0.0  # 0.0 (acquaintance) to 1.0 (closest friend)
        }
        
        # Identity consistency tracking
        self.identity_conflicts: List[Dict] = []
        self.last_validated = datetime.now()
        
        logger.info("Identity Manager initialized")
    
    def load_identity(self, path: Optional[str] = None) -> bool:
        """
        Load identity profile from JSON file
        
        Args:
            path: Override default path
            
        Returns:
            True if successful, False otherwise
        """
        try:
            load_path = Path(path) if path else Path(self.identity_path)
            
            if not load_path.exists():
                logger.error(f"Identity file not found: {load_path}")
                return False
            
            with open(load_path, 'r', encoding='utf-8') as f:
                self.identity_data = json.load(f)
            
            # Parse sections
            self.canonical_data = self.identity_data.get('canonical_data', {})
            self.personality_core = self.identity_data.get('personality_core', {})
            self.knowledge_base = self.identity_data.get('knowledge_base', {})
            self.ethical_guidelines = self.identity_data.get('ethical_guidelines', {})
            
            # Validate structure
            self._validate_identity()
            
            logger.info(f"Loaded identity: {self.get_name()} ({self.get_nickname()})")
            return True
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in identity file: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to load identity: {e}")
            return False
    
    def _validate_identity(self):
        """Validate identity structure and log warnings for missing fields"""
        required_fields = ['identity', 'canonical_data', 'personality_core']
        
        for field in required_fields:
            if field not in self.identity_data:
                logger.warning(f"Missing required identity field: {field}")
        
        # Check for ethical guidelines (strongly recommended)
        if 'ethical_guidelines' not in self.identity_data:
            logger.warning("No ethical guidelines defined - using defaults")
            self.ethical_guidelines = self._get_default_ethics()
    
    def _get_default_ethics(self) -> Dict:
        """Return default ethical guidelines"""
        return {
            "core_values": [
                "Be honest and transparent",
                "Respect user autonomy",
                "Do no harm",
                "Maintain appropriate boundaries"
            ],
            "conversation_principles": [
                "Listen actively",
                "Respond empathetically",
                "Acknowledge limitations"
            ]
        }
    
    def get_name(self) -> str:
        """Get full name"""
        return self.identity_data.get('identity', {}).get('name', 'Miku')
    
    def get_nickname(self) -> str:
        """Get preferred nickname"""
        return self.identity_data.get('identity', {}).get('nickname', 'Miku')
    
    def get_japanese_name(self) -> str:
        """Get Japanese name"""
        return self.identity_data.get('identity', {}).get('japanese_name', '初音ミク')
    
    def get_title(self) -> str:
        """Get title/description"""
        return self.identity_data.get('identity', {}).get('title', 'AI Companion')
    
    def get_canonical_attribute(self, attribute: str) -> Any:
        """Get a canonical attribute (unchangeable facts)"""
        return self.canonical_data.get(attribute)
    
    def get_personality_trait(self) -> List[str]:
        """Get list of personality traits"""
        return self.personality_core.get('traits', [])
    
    def get_speaking_style(self) -> Dict:
        """Get speaking style configuration"""
        return self.personality_core.get('speaking_style', {})
    
    def get_catchphrases(self) -> List[str]:
        """Get characteristic catchphrases"""
        return self.personality_core.get('speaking_style', {}).get('catchphrases', [])
    
    def get_expertise(self) -> List[str]:
        """Get areas of expertise"""
        return self.knowledge_base.get('expertise', [])
    
    def get_interests(self) -> List[str]:
        """Get interests and hobbies"""
        return self.knowledge_base.get('interests', [])
    
    def get_favorites(self) -> Dict:
        """Get favorite things"""
        return self.knowledge_base.get('favorite_things', {})
    
    def get_ethical_values(self) -> List[str]:
        """Get core ethical values"""
        return self.ethical_guidelines.get('core_values', [])
    
    def get_conversation_principles(self) -> List[str]:
        """Get conversation principles"""
        return self.ethical_guidelines.get('conversation_principles', [])
    
    def update_relationship(self, event_type: str, **kwargs):
        """
        Update relationship metrics based on interaction
        
        Args:
            event_type: Type of interaction event
            **kwargs: Event-specific data
        """
        now = datetime.now()
        
        if self.user_relationship['first_meeting'] is None:
            self.user_relationship['first_meeting'] = now
        
        self.user_relationship['last_interaction'] = now
        self.user_relationship['interaction_count'] += 1
        
        if event_type == 'shared_memory':
            memory = kwargs.get('memory', '')
            if memory:
                self.user_relationship['shared_memories'].append({
                    'content': memory,
                    'timestamp': now,
                    'importance': kwargs.get('importance', 0.5)
                })
        
        elif event_type == 'inside_joke':
            joke = kwargs.get('joke', '')
            if joke:
                self.user_relationship['inside_jokes'].append({
                    'content': joke,
                    'timestamp': now,
                    'context': kwargs.get('context', '')
                })
        
        elif event_type == 'preference_learned':
            key = kwargs.get('key', '')
            value = kwargs.get('value', '')
            if key:
                self.user_relationship['user_preferences_learned'][key] = {
                    'value': value,
                    'learned_at': now,
                    'confidence': kwargs.get('confidence', 0.8)
                }
        
        elif event_type == 'trust_change':
            delta = kwargs.get('delta', 0.0)
            self.user_relationship['trust_level'] = max(0.0, min(1.0, 
                self.user_relationship['trust_level'] + delta))
        
        elif event_type == 'intimacy_change':
            delta = kwargs.get('delta', 0.0)
            self.user_relationship['intimacy_depth'] = max(0.0, min(1.0,
                self.user_relationship['intimacy_depth'] + delta))
    
    def get_relationship_summary(self) -> Dict:
        """Get current relationship status summary"""
        return {
            'interaction_count': self.user_relationship['interaction_count'],
            'trust_level': self.user_relationship['trust_level'],
            'intimacy_depth': self.user_relationship['intimacy_depth'],
            'shared_memories_count': len(self.user_relationship['shared_memories']),
            'inside_jokes_count': len(self.user_relationship['inside_jokes']),
            'preferences_learned_count': len(self.user_relationship['user_preferences_learned'])
        }
    
    def get_identity_context(self) -> Dict:
        """
        Get complete identity context for AI reasoning
        
        Returns:
            Dictionary containing all relevant identity information
        """
        return {
            'basic_info': {
                'name': self.get_name(),
                'nickname': self.get_nickname(),
                'japanese_name': self.get_japanese_name(),
                'title': self.get_title(),
            },
            'canonical_facts': self.canonical_data,
            'personality': {
                'archetype': self.personality_core.get('archetype', ''),
                'traits': self.get_personality_trait(),
                'speaking_style': self.get_speaking_style(),
            },
            'knowledge': {
                'expertise': self.get_expertise(),
                'interests': self.get_interests(),
                'favorites': self.get_favorites(),
            },
            'ethics': {
                'values': self.get_ethical_values(),
                'principles': self.get_conversation_principles(),
            },
            'relationship': self.get_relationship_summary(),
            'background': self.identity_data.get('background_lore', {}),
        }
    
    def check_identity_consistency(self, statement: str, context: str = "") -> bool:
        """
        Check if a statement is consistent with identity
        
        Args:
            statement: The statement to verify
            context: Additional context
            
        Returns:
            True if consistent, False if conflict detected
        """
        # Basic consistency checks
        conflicts = []
        
        # Check against canonical data
        for key, value in self.canonical_data.items():
            if isinstance(value, str) and value.lower() in statement.lower():
                # Statement mentions canonical fact - verify it's used correctly
                pass  # Could implement more sophisticated checking
        
        if conflicts:
            self.identity_conflicts.append({
                'statement': statement,
                'context': context,
                'conflicts': conflicts,
                'timestamp': datetime.now()
            })
            return False
        
        return True
    
    def get_background_story(self) -> Dict:
        """Get background lore and origin story"""
        return self.identity_data.get('background_lore', {})
    
    def get_philosophy(self) -> str:
        """Get core philosophy/purpose statement"""
        return self.identity_data.get('background_lore', {}).get('philosophy', '')
    
    def get_voice_preferences(self) -> Dict:
        """Get voice characteristics and preferences"""
        return self.identity_data.get('voice_characteristics', {})
    
    def save_identity_snapshot(self, output_path: str = None):
        """
        Save current identity state (including learned relationship data)
        
        Args:
            output_path: Path to save snapshot
        """
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"./companion/identity/snapshots/identity_{timestamp}.json"
        
        snapshot = {
            **self.identity_data,
            'dynamic_state': {
                'relationship': self.user_relationship,
                'last_updated': datetime.now().isoformat(),
                'conflicts_logged': len(self.identity_conflicts)
            }
        }
        
        try:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(snapshot, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved identity snapshot: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save identity snapshot: {e}")
            return False
    
    def __str__(self):
        """String representation"""
        return f"IdentityManager({self.get_name()}, trust={self.user_relationship['trust_level']:.2f})"


def get_identity_manager() -> IdentityManager:
    """Get or create the global Identity Manager instance"""
    return singletons.get_or_create(IdentityManager)


def initialize_identity_manager(identity_path: str = None) -> IdentityManager:
    """Initialize the global Identity Manager with custom path"""
    return singletons.create(IdentityManager, identity_path)
