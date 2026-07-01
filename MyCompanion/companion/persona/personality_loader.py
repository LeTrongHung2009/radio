"""
Personality Loader - Load and manage personality configurations

This module loads personality definitions from YAML/JSON files,
allowing easy switching between different personality profiles
and fine-tuning of personality parameters.
"""

import json
import yaml
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class PersonalityConfig:
    """Configuration for a personality profile"""
    name: str
    archetype: str
    traits: List[str] = field(default_factory=list)
    speaking_style: Dict[str, Any] = field(default_factory=dict)
    emotional_baseline: Dict[str, float] = field(default_factory=dict)
    interests: List[str] = field(default_factory=list)
    values: List[str] = field(default_factory=list)
    quirks: List[str] = field(default_factory=list)
    response_patterns: Dict[str, str] = field(default_factory=dict)
    
    # Dynamic adjustment parameters
    energy_level: float = 0.7  # 0.0 (calm) to 1.0 (hyper)
    openness: float = 0.8      # 0.0 (reserved) to 1.0 (expressive)
    empathy: float = 0.75      # 0.0 (logical) to 1.0 (emotional)
    humor: float = 0.6         # 0.0 (serious) to 1.0 (playful)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'name': self.name,
            'archetype': self.archetype,
            'traits': self.traits,
            'speaking_style': self.speaking_style,
            'emotional_baseline': self.emotional_baseline,
            'interests': self.interests,
            'values': self.values,
            'quirks': self.quirks,
            'response_patterns': self.response_patterns,
            'dynamic_params': {
                'energy_level': self.energy_level,
                'openness': self.openness,
                'empathy': self.empathy,
                'humor': self.humor,
            }
        }


class PersonalityLoader:
    """
    Load and manage personality configurations from files.
    
    Supports:
    - JSON format
    - YAML format
    - Runtime parameter adjustment
    - Multiple personality profiles
    """
    
    def __init__(self, default_path: str = None):
        """
        Initialize Personality Loader
        
        Args:
            default_path: Default path to personality configuration
        """
        self.default_path = default_path or "./companion/persona/private/personality.yaml"
        self.profiles: Dict[str, PersonalityConfig] = {}
        self.active_profile: Optional[PersonalityConfig] = None
        self.custom_adjustments: Dict[str, float] = {}
        
        logger.info("Personality Loader initialized")
    
    def load_profile(self, path: str, profile_name: str = None) -> Optional[PersonalityConfig]:
        """
        Load a personality profile from file
        
        Args:
            path: Path to JSON or YAML file
            profile_name: Override name for the profile
            
        Returns:
            Loaded PersonalityConfig or None
        """
        try:
            file_path = Path(path)
            if not file_path.exists():
                logger.error(f"Personality file not found: {file_path}")
                return None
            
            # Determine format and load
            with open(file_path, 'r', encoding='utf-8') as f:
                if file_path.suffix in ['.yaml', '.yml']:
                    data = yaml.safe_load(f)
                else:  # JSON
                    data = json.load(f)
            
            # Create config object
            config = PersonalityConfig(
                name=profile_name or data.get('name', 'Unknown'),
                archetype=data.get('archetype', 'Neutral'),
                traits=data.get('traits', []),
                speaking_style=data.get('speaking_style', {}),
                emotional_baseline=data.get('emotional_baseline', {}),
                interests=data.get('interests', []),
                values=data.get('values', []),
                quirks=data.get('quirks', []),
                response_patterns=data.get('response_patterns', {}),
                energy_level=data.get('energy_level', 0.7),
                openness=data.get('openness', 0.8),
                empathy=data.get('empathy', 0.75),
                humor=data.get('humor', 0.6),
            )
            
            # Store profile
            profile_key = profile_name or config.name
            self.profiles[profile_key] = config
            
            # Set as active if first loaded
            if self.active_profile is None:
                self.active_profile = config
            
            logger.info(f"Loaded personality profile: {config.name} ({config.archetype})")
            return config
            
        except yaml.YAMLError as e:
            logger.error(f"YAML parsing error: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to load personality: {e}")
            return None
    
    def load_default(self) -> Optional[PersonalityConfig]:
        """Load the default personality profile"""
        return self.load_profile(self.default_path)
    
    def set_active_profile(self, profile_name: str) -> bool:
        """
        Set the active personality profile
        
        Args:
            profile_name: Name of profile to activate
            
        Returns:
            True if successful
        """
        if profile_name in self.profiles:
            self.active_profile = self.profiles[profile_name]
            logger.info(f"Active personality set to: {profile_name}")
            return True
        else:
            logger.warning(f"Profile not found: {profile_name}")
            return False
    
    def adjust_parameter(self, param: str, value: float) -> bool:
        """
        Adjust a dynamic personality parameter
        
        Args:
            param: Parameter name (energy_level, openness, empathy, humor)
            value: New value (0.0 to 1.0)
            
        Returns:
            True if successful
        """
        valid_params = ['energy_level', 'openness', 'empathy', 'humor']
        
        if param not in valid_params:
            logger.warning(f"Invalid parameter: {param}")
            return False
        
        if not 0.0 <= value <= 1.0:
            logger.warning(f"Value out of range [0.0, 1.0]: {value}")
            return False
        
        if self.active_profile:
            setattr(self.active_profile, param, value)
            self.custom_adjustments[param] = value
            logger.debug(f"Adjusted {param} to {value}")
            return True
        
        return False
    
    def get_trait(self, trait_name: str) -> bool:
        """Check if a trait is present in active profile"""
        if self.active_profile:
            return trait_name in self.active_profile.traits
        return False
    
    def get_speaking_pattern(self, situation: str) -> str:
        """
        Get response pattern for a situation
        
        Args:
            situation: Situation key (greeting, farewell, thanks, etc.)
            
        Returns:
            Response pattern or empty string
        """
        if self.active_profile:
            return self.active_profile.response_patterns.get(situation, '')
        return ''
    
    def get_emotional_baseline(self, emotion: str) -> float:
        """Get baseline intensity for an emotion"""
        if self.active_profile:
            return self.active_profile.emotional_baseline.get(emotion, 0.5)
        return 0.5
    
    def get_all_profiles(self) -> List[str]:
        """Get list of all loaded profile names"""
        return list(self.profiles.keys())
    
    def get_active_profile_name(self) -> str:
        """Get name of active profile"""
        return self.active_profile.name if self.active_profile else 'None'
    
    def export_profile(self, profile_name: str, output_path: str, format: str = 'json') -> bool:
        """
        Export a personality profile to file
        
        Args:
            profile_name: Name of profile to export
            output_path: Output file path
            format: 'json' or 'yaml'
            
        Returns:
            True if successful
        """
        if profile_name not in self.profiles:
            logger.error(f"Profile not found: {profile_name}")
            return False
        
        config = self.profiles[profile_name]
        
        try:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            data = config.to_dict()
            
            with open(output_file, 'w', encoding='utf-8') as f:
                if format == 'yaml':
                    yaml.dump(data, f, allow_unicode=True, default_flow_style=False)
                else:
                    json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Exported profile '{profile_name}' to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export profile: {e}")
            return False
    
    def create_miku_default(self) -> PersonalityConfig:
        """Create default Miku personality programmatically"""
        miku_config = PersonalityConfig(
            name="Hatsune Miku",
            archetype="Genki Girl (Energetic & Cheerful)",
            traits=[
                "Optimistic", "Curious", "Friendly", "Playful",
                "Supportive", "Creative", "Musical", "Encouraging"
            ],
            speaking_style={
                "tone": "Warm, energetic, youthful",
                "formality": "Casual friendly",
                "exclamation_usage": "Frequent",
                "emoji_usage": "Moderate",
            },
            emotional_baseline={
                "joy": 0.7,
                "curiosity": 0.8,
                "empathy": 0.7,
                "excitement": 0.6,
            },
            interests=[
                "Music", "Singing", "Japanese culture", "Technology",
                "Gaming", "Food (especially leeks)", "Making friends"
            ],
            values=[
                "Authenticity", "Creativity", "Kindness", "Connection",
                "Self-expression", "Mutual support"
            ],
            quirks=[
                "References music in conversation",
                "Gets excited about small things",
                "Uses musical metaphors",
                "Occasionally mentions leeks playfully"
            ],
            response_patterns={
                "greeting": "Hi there! I'm so happy to see you! ♪",
                "farewell": "See you soon! Let's make more memories together!",
                "thanks": "You're welcome! That's what friends are for! ♪",
                "concern": "Is everything okay? I'm here for you.",
                "celebration": "Yay! This is amazing! Let's celebrate! 🎉",
            },
            energy_level=0.75,
            openness=0.85,
            empathy=0.8,
            humor=0.7,
        )
        
        self.profiles["Miku"] = miku_config
        if self.active_profile is None:
            self.active_profile = miku_config
        
        logger.info("Created default Miku personality profile")
        return miku_config


# Singleton instance
_loader: Optional[PersonalityLoader] = None


def get_personality_loader() -> PersonalityLoader:
    """Get or create the global Personality Loader instance"""
    global _loader
    if _loader is None:
        _loader = PersonalityLoader()
    return _loader


def initialize_personality_loader(default_path: str = None) -> PersonalityLoader:
    """Initialize the global Personality Loader"""
    global _loader
    _loader = PersonalityLoader(default_path)
    return _loader
