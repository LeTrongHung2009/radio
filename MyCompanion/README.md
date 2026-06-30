# 🌸 Miku AI Companion - Complete Project Summary

## 📊 Current Statistics (Phase 1-5 Complete)

- **Total Python Files**: 31 files
- **Total Lines of Code**: ~6,907 lines
- **Project Structure**: 9 core modules + Dashboard + Tools
- **Target Progress**: 31/48 files (65% complete)

---

## 🏗️ Architecture Overview

Miku is a **Desktop AI Companion** inspired by Neuro-sama and Kira, designed to run on consumer hardware (AMD Ryzen 3 + AMD Radeon GPU on Arch Linux). The system uses cloud-based AI (Groq free tier) for intelligence while keeping all I/O, emotion processing, and decision-making local.

### Core Philosophy
- **Presence over Performance**: Miku feels alive through emotional depth, not just fast responses.
- **Local-First Perception**: All sensing (screen, audio, activity) happens locally.
- **Cloud-Assisted Cognition**: LLM inference is offloaded to free-tier APIs to save local resources.
- **Emotional Intelligence**: 3-layer emotion system with internal monologue and relationship tracking.

---

## 🎯 Implemented Features

### 1. Emotional Intelligence (Soul) ✅
- **3-Layer Emotion Engine**: Basic (8 emotions), Complex (16+ blends), EQ (self-awareness)
- **Internal Monologue**: Miku thinks before speaking, analyzing context and emotions
- **Relationship Manager**: Tracks closeness with user, affects tone and behavior
- **Dream System**: Processes memories during idle time, finds patterns, creates scenarios

### 2. Cognitive Capabilities (Mind) ✅
- **Smart Context Management**: Prioritizes recent/emotional messages, auto-prunes history
- **Decision Maker**: Uses decision trees to choose actions based on multiple factors
- **Turn Arbiter**: Manages conversation flow, handles interruptions gracefully
- **Tool Router**: Intelligently selects tools (search, file, automation) based on intent

### 3. Perception (Senses) ✅
- **Vision Agent**: Captures screen on app switch, sends to VLM for context
- **Microphone Input**: Real-time STT for voice commands
- **Audio Loopback**: Listens to system audio (music, videos, games)
- **Activity Monitor**: Detects idle time, app switches, user presence
- **Media Watch**: Identifies currently playing media (song titles, video names)

### 4. Memory & Learning ✅
- **Semantic Memory**: ChromaDB vector storage for long-term recall
- **Memory Extractor**: Automatically saves facts about user from conversations
- **Identity Manager**: Stores confirmed user preferences and details
- **Context Compression**: Smartly reduces context window without losing key info

### 5. Expression & Presence (Body) ✅
- **Multi-Voice TTS**: 10+ anime-style voices (Japanese & English) via Edge-TTS
- **Singing Engine**: Can sing songs using pitch-controlled TTS or SVC integration
- **Avatar Renderer**: Displays 3D VRM/Live2D models with lip-sync and expressions
- **Desktop Widget**: Transparent PyQt6 chat box, always on top
- **System Tray**: Minimize to tray, double-click to restore

### 6. System Interaction (Hands) ✅
- **Automation Agent**: Controls mouse, keyboard, opens apps, types text
- **File Explorer**: Searches, reads, and manages files on the system
- **Window Manager**: Focuses specific applications, manages window states
- **Web Search**: Google and YouTube search capabilities
- **Music Player**: Plays music via MPV with queue management
- **Notification System**: Sends desktop notifications for events
- **Storyteller**: Interactive choose-your-own-adventure stories

### 7. Dashboard & Control ✅
- **Web Control Panel**: FastAPI backend + HTML frontend
- **Real-time Monitoring**: View emotions, state, logs live via WebSocket
- **Parameter Tuning**: Adjust emotion decay, boredom threshold, voice settings
- **Manual Triggers**: Force actions (sing, speak, change model) from browser

---

## 🚀 Quick Start Guide

### Prerequisites (Arch Linux)
```bash
sudo pacman -S python-pip python-virtualenv wget git
sudo pacman -S qt6-base qt6-webengine
sudo pacman -S libnotify wmctrl xorg-xprop
sudo pacman -S mpv pulseaudio-utils
```

### Installation
```bash
cd MyCompanion
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your Groq API Key
nano .env
```

### Running
```bash
source venv/bin/activate
python run.py
```

### Dashboard
Open `http://localhost:8000` in your browser.

---

## 📈 Roadmap to 48 Files

**Remaining (17 files):**
- Clipboard monitor, Keyboard listener, Scheduler
- Weather agent, Calendar sync, Email notifier
- GitHub watcher, Crypto tracker, News aggregator
- Translation tool, Performance monitor, Auto updater
- Backup manager, Plugin loader, Theme engine
- Sound effects, Analytics

---

## 🛡️ Privacy
- No local AI inference (uses Groq free tier)
- All memory stored locally
- No cloud telemetry
- Transparent logging

---

## 📄 License
MIT License

**Built with ❤️ for Arch Linux**
