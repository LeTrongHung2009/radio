# MyCompanion - Autonomous AI Desktop Companion

An autonomous, interactive AI Desktop Companion framework inspired by [Neuro-sama](https://virtualyoutuber.fandom.com/wiki/Neuro-sama). Lives on your monitor, observes your desktop, listens via microphone, speaks Vietnamese, and acts like a living entity — all optimized for constrained hardware.

**No livestreaming. No VTuber Studio requirement. Pure local desktop companion.**

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                        app.py (Orchestrator)                  │
├──────────┬──────────┬──────────┬──────────┬──────────────────┤
│  Brain   │ Persona  │  Senses  │Expression│     Desktop      │
│ ┌──────┐ │ ┌──────┐ │ ┌──────┐ │ ┌──────┐ │ ┌──────────────┐ │
│ │Cortex│ │ │Emot. │ │ │Vision│ │ │ VTS  │ │ │  Chat Widget │ │
│ │      │ │ │Matrix│ │ │Agent │ │ │Connct│ │ │  (PyQt6)     │ │
│ ├──────┤ │ ├──────┤ │ ├──────┤ │ ├──────┤ │ ├──────────────┤ │
│ │ API  │ │ │Prompt│ │ │ STT  │ │ │Expr. │ │ │   Spatial    │ │
│ │Router│ │ │Engine│ │ │Pipe  │ │ │ Map  │ │ │   Engine     │ │
│ ├──────┤ │ └──────┘ │ ├──────┤ │ ├──────┤ │ └──────────────┘ │
│ │Rate  │ │          │ │Contxt│ │ │ TTS  │ │                  │
│ │Limit │ │          │ │Reader│ │ │Engine│ │                  │
│ ├──────┤ │          │ └──────┘ │ └──────┘ │                  │
│ │Prior.│ │          │          │          │                  │
│ │Queue │ │          │          │          │                  │
│ ├──────┤ │          │          │          │                  │
│ │Turn  │ │          │          │          │                  │
│ │Ctrl  │ │          │          │          │                  │
│ └──────┘ │          │          │          │                  │
├──────────┴──────────┴──────────┴──────────┴──────────────────┤
│  Dream Engine  │  Learning (SQLite)  │  Model Setup (#4711410)│
└────────────────┴─────────────────────┴───────────────────────┘
```

### 8 Core Pipelines

| # | Pipeline | Module | Description |
|---|----------|--------|-------------|
| 1 | **AI Cortex** | `companion/brain/` | API routing (Groq→OpenAI→Anthropic), token-bucket rate limiter, priority queue, turn-taking |
| 2 | **Senses** | `companion/senses/` | Screen capture via `mss`, STT via `sounddevice` + Groq Whisper, window tracking via `xdotool` |
| 3 | **Voice & Animation** | `companion/expression/` | TTS via `edge-tts` (vi-VN-HoaiMyNeural), VTube Studio WebSocket bridge, lip sync |
| 4 | **Emotional System** | `companion/persona/` | 3-layer emotion matrix (reflex/mood/core traits), dynamic prompt generator |
| 5 | **Desktop UI** | `companion/desktop/` | PyQt6 frameless chat widget, spatial awareness, collision avoidance |
| 6 | **Spatial Awareness** | `companion/desktop/` | Active window collision detection, auto-reposition, idle levitation |
| 7 | **Dream Engine** | `companion/dream/` | Cognitive sleep after 10min idle, memory consolidation, context seed generation |
| 8 | **Learning** | `companion/learning/` | SQLite + JSON memory store, regex fact extraction |

### 3-Layer Emotional Matrix

| Layer | Name | Behavior |
|-------|------|----------|
| 1 | Reflexive Reaction | Instantaneous response to events, decays in seconds |
| 2 | Ambient Mood | Slow drift based on interaction sentiment over minutes |
| 3 | Core Personality | **Immutable**: sassy, sharp-witted, curious, cute, deeply attached |

### Event Priority System

| Priority | Event Type | Weight |
|----------|-----------|--------|
| 0 (highest) | User Text Input | Immediate |
| 1 | Voice Interrupt | High |
| 2 | Screen Change | Medium |
| 3 | Boredom Prompt | Low |

---

## Hardware Requirements

| Component | Specification |
|-----------|---------------|
| CPU | AMD Ryzen 3 3000+ (or equivalent) |
| GPU | AMD Radeon onboard (**NO CUDA**) |
| RAM | 8GB DDR4 (framework uses ≤250MB) |
| OS | **Arch Linux** with GNOME Desktop |
| Display | X11 or Wayland |

---

## Installation (Arch Linux)

### 1. System Dependencies

```bash
# Core packages
sudo pacman -S python python-pip python-virtualenv

# Audio
sudo pacman -S mpv pulseaudio portaudio

# Screen capture & window tracking
sudo pacman -S xdotool scrot

# Fonts (for PyQt6 Vietnamese rendering)
sudo pacman -S noto-fonts noto-fonts-cjk

# Optional: VTube Studio (install via Steam or standalone)
```

### 2. Python Environment

```bash
cd MyCompanion
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Configuration

```bash
cp .env.example .env
# Edit .env and add your API keys:
#   GROQ_API_KEY=gsk_...        (required - free tier)
#   OPENAI_API_KEY=sk-...       (optional fallback)
#   ANTHROPIC_API_KEY=sk-ant-.. (optional fallback)
```

### 4. Run

```bash
# With GUI (default)
python app.py

# Headless mode (no display required)
MYCOMPANION_HEADLESS=1 python app.py
```

---

## API Configuration

### Groq (Primary - Free Tier)

1. Sign up at https://console.groq.com
2. Create an API key
3. Set `GROQ_API_KEY` in `.env`
4. Uses `llama-3.3-70b-versatile` by default

### Fallback Providers

The system automatically falls back through providers on rate limit (429) or errors:

```
Groq (free) → OpenAI → Anthropic
```

Each provider has its own token-bucket rate limiter to prevent 429 errors.

---

## Live2D Model (Booth #4711410)

| Field | Value |
|-------|-------|
| Source | https://booth.pm/en/items/4711410 |
| Type | Half-Body Live2D Model |
| Art Credit | **@koahri1** |
| Rigger Credit | **@MedL2D** |

To use with VTube Studio:
1. Purchase and download the model from Booth
2. Import into VTube Studio
3. Enable VTS in `.env`: `VTS_ENABLED=true`
4. The connector auto-authenticates via WebSocket at `ws://127.0.0.1:8001`

---

## Project Structure

```
MyCompanion/
├── app.py                              # Global Orchestrator
├── requirements.txt                    # Pinned dependencies
├── .env.example                        # API key template
├── README.md                           # This file
└── companion/
    ├── brain/
    │   ├── cortex.py                   # Central cognitive loop
    │   ├── api_router.py               # Multi-provider LLM router
    │   ├── rate_limiter.py             # Token-bucket rate limiter
    │   ├── priority_queue.py           # Event priority queue
    │   └── turn_controller.py          # Turn-taking orchestration
    ├── persona/
    │   ├── emotion_matrix.py           # 3-layer emotional state
    │   └── prompt_engine.py            # Dynamic prompt builder
    ├── senses/
    │   ├── vision_agent.py             # Screen capture (mss)
    │   ├── stt_pipeline.py             # Microphone STT (Groq Whisper)
    │   └── context_reader.py           # Window tracking (xdotool)
    ├── expression/
    │   ├── vts_connector.py            # VTube Studio WebSocket
    │   ├── vts_expression_map.py       # Emotion → Live2D params
    │   └── tts_engine.py               # Text-to-Speech (edge-tts)
    ├── desktop/
    │   ├── chat_widget.py              # PyQt6 frameless chat UI
    │   └── spatial_engine.py           # Collision avoidance
    ├── dream/
    │   └── dream_engine.py             # Cognitive sleep & consolidation
    ├── learning/
    │   ├── memory_store.py             # SQLite + JSON datastore
    │   └── fact_extractor.py           # Personal fact mining
    └── model_setup/
        ├── vts_config.py               # Booth #4711410 VTS config
        └── attribution.py              # License attribution
```

---

## Troubleshooting

### No audio output
```bash
# Check PulseAudio is running
pulseaudio --check && echo "running" || pulseaudio --start

# Test mpv
echo "test" | mpv --no-video -
```

### xdotool not working (Wayland)
```bash
# xdotool requires X11. On Wayland, install xdotool compatibility:
sudo pacman -S xdotool
# Or switch to X11 session in GDM
```

### PyQt6 display issues
```bash
# Ensure DISPLAY is set
echo $DISPLAY  # should show :0 or :1

# For Wayland
export QT_QPA_PLATFORM=wayland
```

### High memory usage
```bash
# Check companion memory usage
ps aux | grep app.py
# Should be under 250MB RSS
```

### Groq rate limits
The built-in token-bucket limiter handles this automatically. If you see frequent 429 errors, the system will:
1. Wait and retry with exponential backoff
2. Fall back to OpenAI/Anthropic if configured

---

## License

This project uses the Booth #4711410 Live2D model under the creator's license terms.
- Art: @koahri1
- Rigger: @MedL2D
- Source: https://booth.pm/en/items/4711410
