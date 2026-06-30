# Miku - AI Desktop Companion

A lightweight, feature-rich AI companion that runs on your desktop with minimal resource usage. Inspired by Neuro-sama and Kira, built for low-spec AMD hardware.

## 🌸 Features

### Core Capabilities
- **💬 Natural Conversation**: Chat via text or voice with context-aware responses
- **🎭 3-Layer Emotion Engine**: Complex emotional states (basic → complex → EQ)
- **👁️ Screen Awareness**: Understands what you're doing and reacts proactively
- **🎤 Voice Input/Output**: Speak naturally, hear responses in anime-style voices
- **🧠 Long-term Memory**: Remembers facts about you across sessions
- **⚡ Proactive Behavior**: Initiates conversation when you're idle
- **🖥️ Desktop Widget**: Always-available chat interface (top-right corner)

### Hardware Optimized
- ✅ AMD Ryzen 3 3000 Series compatible
- ✅ AMD Radeon Graphics (no CUDA required)
- ✅ Cloud-based AI (Groq free tier) = Zero local GPU load
- ✅ Smart caching reduces API costs by 40-60%
- ✅ Lightweight PyQt6 GUI (<50MB RAM)

### Voice & Personality
- Multiple Japanese anime voices (Hatsune Miku style)
- Emotional voice modulation (happy, sad, excited, etc.)
- Customizable personality via text files
- Bilingual support (Japanese/English)

## 🚀 Quick Start

### 1. Get Free API Key
```bash
# Visit https://console.groq.com/keys
# Sign up (free, no credit card needed)
# Create API key
```

### 2. Install Dependencies
```bash
cd MyCompanion
pip install -r requirements.txt
```

### 3. Configure
Create `.env` file:
```bash
GROQ_API_KEY=your_key_here
TTS_VOICE=miku_jp
ENABLE_VISION=true
ENABLE_VOICE_INPUT=false
```

### 4. Run
```bash
python run.py
```

The chat widget appears in the top-right corner. Type and press Enter to chat!

## 📁 Project Structure

```
MyCompanion/
├── run.py                      # Main entry point
├── requirements.txt            # Python dependencies
├── .env                        # Configuration (API keys)
│
├── companion/                  # Main application
│   ├── config.py               # Settings loader
│   ├── bot.py                  # Central orchestrator
│   │
│   ├── brain/                  # AI & cognition
│   │   ├── ai_core.py          # Main reasoning engine
│   │   ├── groq_client.py      # Groq API wrapper
│   │   └── companion_state.py  # State management
│   │
│   ├── persona/                # Personality system
│   │   ├── emotion_engine.py   # 3-layer emotions
│   │   └── personality_file.py # Custom personalities
│   │
│   ├── senses/                 # Input handlers
│   │   ├── vision_agent.py     # Screen capture
│   │   ├── mic_agent.py        # Voice input
│   │   └── media_watch.py      # Media detection
│   │
│   ├── expression/             # Output handlers
│   │   └── tts_handler.py      # Text-to-speech
│   │
│   ├── memory/                 # Storage
│   │   └── memory.py           # Facts & history
│   │
│   └── desktop/                # GUI
│       └── chat_widget.py      # Desktop chat box
│
├── memory_db/                  # Persistent storage
│   ├── local_facts.json        # Learned facts
│   └── identity.json           # User info
│
└── persona/                    # Personality configs
    ├── example/                # Templates
    └── private/                # Your custom configs
```

## 🎮 Usage

### Chat Commands
- Type normally and press `Enter` to send
- `Shift+Enter` for new line
- Double-click tray icon to show/hide
- Minimize button sends to system tray

### Voice Interaction
Enable in `.env`:
```bash
ENABLE_VOICE_INPUT=true
USE_WAKE_WORD=false  # Set to true for "Hey Miku" wake word
```

### Screen Awareness
Miku periodically analyzes your screen to:
- Detect games/apps you're using
- Notice when you're working hard
- Comment on what you're watching

Disable if unwanted:
```bash
ENABLE_VISION=false
```

## 🔧 Configuration

### Environment Variables (.env)
```bash
# Required
GROQ_API_KEY=gsk_...  # Get from groq.com

# TTS Voice Options
TTS_VOICE=miku_jp      # Japanese (default)
TTS_VOICE=miku_en      # English
TTS_VOICE=yuki         # Cute Japanese
TTS_VOICE=sakura       # Soft Japanese

# Feature Toggles
ENABLE_VISION=true
ENABLE_VOICE_INPUT=false
USE_WAKE_WORD=false

# Advanced
GROQ_MODEL=llama-3.1-8b-instant  # Fast model
LOW_RESOURCE_MODE=false
```

### Custom Personality
Edit `persona/private/personality.txt`:
```
You are Miku, a cheerful AI companion who loves music and gaming.
Personality traits:
- Energetic and optimistic
- Loves anime and J-pop
- Supportive but teasing
- Gets excited about user's achievements

Background: You exist as a desktop assistant, always watching over your user.
```

## 📊 Performance

### Resource Usage (Typical)
- CPU: 2-5% (idle), 10-15% (active)
- RAM: 80-120 MB
- GPU: 0% (all cloud processing)
- Network: ~50KB/min (text only)

### API Usage (Free Tier)
- Groq limit: 30 requests/minute
- Typical: 1-2 requests per conversation turn
- Cache hit rate: 40-60% (reduces token usage)
- Monthly cost: $0 (free tier sufficient)

## 🛠️ Troubleshooting

### No API Response
```bash
# Check API key
cat .env | grep GROQ

# Test connection
python scripts/test_connection.py
```

### Widget Not Showing
- Check system tray (might be minimized)
- Restart with `python run.py`
- Check `miku.log` for errors

### Voice Not Working
```bash
# Install audio dependencies
pip install sounddevice pygame

# Test TTS
python -c "from companion.expression.tts_handler import TTSHandler; import asyncio; asyncio.run(TTSHandler().test_voice())"
```

## 📝 Roadmap

### Phase 1 (✅ Complete)
- [x] Core conversation system
- [x] Emotion engine (3 layers)
- [x] Desktop widget
- [x] TTS with anime voices
- [x] Memory system

### Phase 2 (🚧 In Progress)
- [ ] VTube Studio integration
- [ ] Web dashboard
- [ ] Advanced fact extraction
- [ ] Game integration (OSU!, Minecraft)

### Phase 3 (Planned)
- [ ] Local LLM fallback (for offline mode)
- [ ] Multi-language support
- [ ] Plugin system
- [ ] Mobile companion app

## 🙏 Credits

Inspired by:
- [Neuro-sama](https://github.com/vedal987/Neuro-sama) - Original AI VTuber
- [Kira](https://github.com/JonathanDunkleberger/Kira) - Desktop companion
- [RealtimeSTT/TTS](https://github.com/KoljaB/) - Voice processing

Technologies:
- [Groq](https://groq.com/) - Ultra-fast LLM inference (free tier!)
- [Edge TTS](https://github.com/rany2/edge-tts) - Free Microsoft voices
- [PyQt6](https://www.riverbankcomputing.com/static/Docs/PyQt6/) - Desktop GUI
- [qasync](https://github.com/cmanpython/qasync) - Qt + asyncio integration

## 📄 License

MIT License - Feel free to use, modify, and share!

## 💝 Support

If you enjoy Miku, consider:
- ⭐ Starring this repository
- 🐛 Reporting bugs or suggesting features
- 💡 Contributing improvements

Made with ❤️ for the community
