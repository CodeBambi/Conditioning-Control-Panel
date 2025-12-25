# 🎀 Conditioning Control Panel v2.0

A sophisticated desktop conditioning application with visual interruption, subliminal messaging, gamification, and progressive unlock system.

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![Platform](https://img.shields.io/badge/Platform-Windows-green.svg)
![Version](https://img.shields.io/badge/Version-2.0-pink.svg)

---

## 📖 Table of Contents

1. [Welcome](#-welcome-bambi)
2. [Quick Start](#-quick-start)
3. [Installation](#-installation)
4. [Interface Overview](#-interface-overview)
5. [Features Guide](#-features-guide)
   - [Flash Images](#-flash-images)
   - [Mandatory Videos](#-mandatory-videos-startle)
   - [Subliminal Messages](#-subliminal-messages)
   - [Progression System](#-progression-system)
   - [Bubble Game](#-bubble-game)
   - [Spiral Overlay](#-spiral-overlay)
   - [Pink Filter](#-pink-filter)
   - [Scheduler](#-scheduler)
   - [Audio System](#-audio-system)
6. [Presets](#-presets)
7. [Settings Reference](#-settings-reference)
8. [Asset Folders](#-asset-folders)
9. [Safety & Warnings](#%EF%B8%8F-safety--warnings)
10. [Troubleshooting](#-troubleshooting)
11. [Keyboard Shortcuts](#-keyboard-shortcuts)
12. [FAQ](#-faq)

---

## 🎀 Welcome, Bambi!

On first launch, you'll see a welcome screen where you can choose how intense you want your experience to be. Don't worry - you can always change settings later!

### Built-in Presets

| Preset | Intensity | Best For |
|--------|-----------|----------|
| 🌸 **Beginner Bimbo** | Low | First-time users, gentle introduction |
| 💄 **Bimbo in Training** | Medium-Low | Getting comfortable, light conditioning |
| 💋 **Advanced Bimbo** | Medium-High | Regular users wanting more intensity |
| 👑 **Ultimate Bimbodoll** | High | Experienced users, intense sessions |

---

## 🚀 Quick Start

1. **Run the application** - Double-click `Conditioning Control Panel.exe`
2. **Choose a preset** - Select from the welcome screen or dropdown menu
3. **Add your content** - Put images in `assets/images/`, videos in `assets/startle_videos/`
4. **Click START** - The pink button begins your session
5. **Press ESC** - Panic stop anytime (unless disabled)

---

## 💿 Installation

### For Compiled Release (.exe)
1. Extract the ZIP file to any folder
2. Run `Conditioning Control Panel.exe`
3. Add your content to the `assets` subfolders

### For Python Source
```bash
# Requirements
- Windows 10/11
- Python 3.8+
- Chrome browser (for embedded player)

# Install dependencies
pip install -r requirements.txt

# Run
python main.py
```

---

## 🖥️ Interface Overview

The application has a 3-column layout:

```
┌─────────────────────────────────────────────────────────────┐
│  🎀 CONDITIONING CONTROL PANEL          Lv.33 [████░] 420XP │
├─────────────────┬─────────────────┬─────────────────────────┤
│   CONTROLS      │    SETTINGS     │       BROWSER           │
│                 │                 │                         │
│ [▶ START]       │ [Settings Tab]  │   Embedded Chrome       │
│ [Preset ▼]      │ [Progression]   │   for audio playback    │
│ [Save] [Load]   │                 │                         │
│                 │ Flash Images    │                         │
│ Quick Toggles:  │ Visuals         │                         │
│ • Flash         │ Mandatory Video │                         │
│ • Video         │ Subliminals     │                         │
│ • Subliminal    │ Audio           │                         │
│ • Dual Monitor  │ Advanced        │                         │
│                 │                 │                         │
└─────────────────┴─────────────────┴─────────────────────────┘
```

### Header Bar
- **Level Display** - Your current level and XP
- **XP Bar** - Progress to next level (hot pink)

### Left Column (Controls)
- **START/STOP** - Main control button
- **Preset Menu** - Load saved configurations
- **Quick Toggles** - Fast on/off for main features

### Middle Column (Settings)
- **Settings Tab** - All configuration options
- **Progression Tab** - Level-locked features (unlocks at Lv.10)

### Right Column (Browser)
- **Embedded Chrome** - Play background audio/video
- **Themed Header** - Covers Chrome UI for cleaner look

---

## 📚 Features Guide

### 📸 Flash Images

Random images from your collection appear on screen at set intervals.

#### Controls

| Setting | Range | Description |
|---------|-------|-------------|
| **Enable** | On/Off | Toggle flash images |
| **Clickable** | On/Off | Can click images to close them |
| **💀 Corruption** | On/Off | Hydra mode - clicking spawns 2 more |
| **Per Min** | 1-10 | How many flash events per minute |
| **Images** | 1-20 | Images shown per flash event |
| **Max On Screen** | 1-20 | Maximum simultaneous images |

#### Visual Settings

| Setting | Range | Description |
|---------|-------|-------------|
| **Size** | 50-250% | Image scale multiplier |
| **Opacity** | 10-100% | Image transparency |
| **Fade** | 0-100% | Fade-out duration when closing |

#### How It Works
1. At each interval, the app selects random images from `assets/images/`
2. Images appear at random positions on screen
3. A sound plays from `assets/sounds/` (if available)
4. If **Clickable** is ON: Click to close
5. If **Corruption** is ON: Clicking spawns 2 new images
6. Images auto-cleanup 1 second after the sound ends

#### Tips
- Use PNG/JPG/GIF formats
- GIFs will animate!
- The app remembers which images it showed to avoid immediate repeats

---

### 🎬 Mandatory Videos (Startle)

Full-screen videos that demand your attention.

#### Controls

| Setting | Range | Description |
|---------|-------|-------------|
| **Enable** | On/Off | Toggle mandatory videos |
| **Per Hour** | 1-30 | Videos per hour |
| **⚠️ Strict Lock** | On/Off | CANNOT close until video ends |
| **Mini-Game** | On/Off | Attention targets during video |
| **Target Density** | 1-10 | How many targets appear |

#### How It Works
1. Video triggers after a random delay (based on Per Hour setting)
2. A 4-second preparation phase clears other effects
3. Video plays fullscreen with audio
4. If **Mini-Game** is enabled, click the pink targets
5. Missing targets = penalties (video restarts, "DUMB BAMBI" screen)
6. After 3 consecutive failures, **Mercy System** releases you

#### Strict Lock Mode
- Window cannot be closed or minimized
- Alt+F4 is blocked
- Only escape: complete the video or fail 3 attention checks
- **Use with caution!**

---

### 💬 Subliminal Messages

Brief text flashes that appear for just a few frames.

#### Controls

| Setting | Range | Description |
|---------|-------|-------------|
| **Enable** | On/Off | Toggle subliminal text |
| **Per Min** | 1-20 | Messages per minute |
| **Frames** | 1-10 | How long text displays (frames) |
| **Opacity** | 10-100% | Text visibility |
| **Audio Whispers** | On/Off | Play audio from sub_audio folder |
| **Edit Phrases** | Button | Customize the text pool |
| **Style** | Button | Change colors and font |

#### Default Phrases
The app comes with a pool of conditioning phrases. You can:
- Enable/disable individual phrases
- Add your own custom phrases
- Customize colors (text, glow, background)

#### Audio Whispers
Place MP3/WAV files in `assets/sub_audio/` and they'll play randomly alongside text.

---

### 🎮 Progression System

Earn XP and unlock features as you level up!

#### XP Sources

| Action | XP Earned |
|--------|-----------|
| Flash image displayed | +2 XP |
| Video watched | +20 XP |
| Bubble popped | +10 XP |
| Attention target clicked | +5 XP |

#### Level Formula
```
XP needed for next level = 50 + (current_level × 20)
```

Example progression:
- Level 1→2: 70 XP
- Level 10→11: 250 XP  
- Level 20→21: 450 XP

#### Unlocks

| Level | Feature Unlocked |
|-------|------------------|
| 1 | Flash Images, Subliminals, Videos |
| 10 | **Spiral Overlay**, **Pink Filter** |
| 20 | **Bubble Pop Game** |
| 50+ | *Coming soon...* |

---

### 🫧 Bubble Game

*(Unlocks at Level 20)*

Floating bubbles rise from the bottom of your screen. Pop them for bonus XP!

#### Controls

| Setting | Range | Description |
|---------|-------|-------------|
| **Enable** | On/Off | Toggle bubble spawning |
| **Per Min** | 1-15 | Bubbles per minute |
| **Link to Ramp** | On/Off | Frequency increases with scheduler |

#### How It Works
1. Bubbles spawn at the bottom of random monitors
2. They float upward with a wobbly animation
3. Click anywhere on the bubble to pop it (+10 XP)
4. Missed bubbles disappear at the top
5. Pop sound plays on click

#### Notes
- Bubbles pause during flash events (no overlap)
- Bubbles auto-pop when videos start
- Maximum 4 bubbles on screen at once
- Frequency reduces when spiral is active (performance)

---

### 🌀 Spiral Overlay

*(Unlocks at Level 10)*

An animated spiral overlay on your screen for enhanced immersion.

#### Controls

| Setting | Description |
|---------|-------------|
| **Enable** | Toggle spiral display |
| **Opacity** | How visible the spiral is (10-100%) |
| **Select File** | Choose your spiral GIF/video |
| **Link to Ramp** | Opacity increases with scheduler intensity |

#### Supported Formats
- GIF (animated)
- MP4, AVI, MOV (video files)

#### Performance Notes
- Spiral runs at 12 FPS to reduce CPU usage
- Automatically pauses during videos
- Reduces bubble frequency when active

---

### 🌸 Pink Filter

*(Unlocks at Level 10)*

A pink tint overlay across your entire screen.

#### Controls

| Setting | Range | Description |
|---------|-------|-------------|
| **Enable** | On/Off | Toggle pink filter |
| **Opacity** | 5-50% | Filter intensity |
| **Link to Ramp** | On/Off | Intensity increases with scheduler |

---

### ⏱️ Scheduler

Gradually increase intensity over time.

#### Controls

| Setting | Range | Description |
|---------|-------|-------------|
| **Enable** | On/Off | Toggle scheduler |
| **Duration** | 5-120 min | Ramp-up time |
| **Multiplier** | 1.0-3.0× | Max frequency multiplier |
| **Time Schedule** | On/Off | Only run during specific hours |

#### How It Works
1. When you start, intensity begins at baseline
2. Over the duration, frequency gradually increases
3. At the end, frequency = baseline × multiplier
4. Features with "Link to Ramp" also scale up

#### Time Schedule
Set specific hours/days when the app is allowed to run:
- Select allowed hours (e.g., 10 PM - 2 AM)
- Select allowed days (e.g., weekends only)
- Outside these times, effects won't trigger

---

### 🔊 Audio System

#### Volume Controls

| Setting | Range | Description |
|---------|-------|-------------|
| **Master Volume** | 0-100% | Overall sound level |
| **Audio Ducking** | On/Off | Lower other apps during effects |
| **Ducking Strength** | 0-100% | How much to lower other apps |

#### Audio Ducking
When enabled, other applications (Spotify, YouTube, etc.) will automatically lower their volume when:
- Flash images appear
- Videos play
- Subliminal audio plays

Requires running as Administrator for full functionality.

#### Sound Folders
- `assets/sounds/` - Flash image sounds
- `assets/sub_audio/` - Subliminal whispers
- `assets/backgrounds/` - Background ambient audio

---

## 🎛️ Presets

### Using Presets

1. **Built-in Presets** - Select from dropdown (🌸 Beginner, 💄 Training, etc.)
2. **Save Current** - Click "Save" to store your configuration
3. **Load Preset** - Select from dropdown to restore settings
4. **DEFAULT** - Resets to factory settings

### Preset Details

#### 🌸 Beginner Bimbo
```
Flash: 1/min, 2 images, no corruption
Video: Disabled
Subliminals: Disabled
Progression features: Disabled
Volume: 25%
```

#### 💄 Bimbo in Training
```
Flash: 2/min, 3 images, no corruption
Video: Enabled, 4/hour, no strict
Subliminals: Enabled, 3/min
Pink Filter: 10% opacity
Bubbles: 3/min
Volume: 35%
```

#### 💋 Advanced Bimbo
```
Flash: 4/min, 5 images, corruption ON
Video: 6/hour, no strict, mini-game ON
Subliminals: 5/min
Scheduler: 30 min ramp
Spiral: 15% opacity
Pink Filter: 15%, linked to ramp
Bubbles: 5/min, linked to ramp
Volume: 45%
```

#### 👑 Ultimate Bimbodoll
```
Flash: 6/min, 7 images, corruption ON
Video: 8/hour, STRICT MODE, mini-game ON
Subliminals: 7/min
Scheduler: 60 min ramp, 1.5× multiplier
Spiral: 20%, linked to ramp
Pink Filter: 20%, linked to ramp
Bubbles: 7/min, linked to ramp
Volume: 55%
```

---

## ⚙️ Settings Reference

### Complete Settings List

#### Flash Images
| Key | Default | Description |
|-----|---------|-------------|
| `flash_enabled` | true | Enable flash images |
| `flash_freq` | 2 | Flashes per minute |
| `flash_clickable` | true | Allow clicking to close |
| `flash_corruption` | false | Hydra mode |
| `flash_hydra_limit` | 20 | Max images (hard cap) |
| `sim_images` | 5 | Images per flash |
| `image_scale` | 0.9 | Size multiplier |
| `image_alpha` | 1.0 | Opacity |
| `fade_duration` | 0.4 | Fade time (seconds) |

#### Video
| Key | Default | Description |
|-----|---------|-------------|
| `startle_enabled` | true | Enable videos |
| `startle_freq` | 5 | Videos per hour |
| `startle_strict` | false | Strict lock mode |
| `attention_enabled` | false | Mini-game targets |
| `attention_density` | 3 | Target count |

#### Subliminals
| Key | Default | Description |
|-----|---------|-------------|
| `subliminal_enabled` | false | Enable text flashes |
| `subliminal_freq` | 5 | Messages per minute |
| `subliminal_duration` | 2 | Frames displayed |
| `subliminal_opacity` | 0.7 | Text opacity |
| `sub_audio_enabled` | false | Audio whispers |

#### Progression
| Key | Default | Description |
|-----|---------|-------------|
| `player_level` | 1 | Current level |
| `player_xp` | 0 | Current XP |
| `pink_filter_enabled` | false | Pink overlay |
| `pink_filter_opacity` | 0.1 | Filter strength |
| `spiral_enabled` | false | Spiral overlay |
| `spiral_opacity` | 0.1 | Spiral visibility |
| `bubbles_enabled` | false | Bubble game |
| `bubbles_freq` | 5 | Bubbles per minute |

#### Audio
| Key | Default | Description |
|-----|---------|-------------|
| `volume` | 0.5 | Master volume |
| `audio_ducking_enabled` | true | Auto-duck other apps |
| `audio_ducking_strength` | 80 | Ducking percentage |

#### System
| Key | Default | Description |
|-----|---------|-------------|
| `dual_monitor` | false | Multi-monitor support |
| `disable_panic_esc` | false | Disable ESC panic key |
| `start_minimized` | false | Start in system tray |
| `auto_start_engine` | false | Auto-start on launch |

---

## 📁 Asset Folders

```
assets/
├── images/           # Flash images (PNG, JPG, GIF)
│   └── bubble.png    # Bubble game sprite
├── sounds/           # Flash sound effects
│   ├── Pop.mp3       # Bubble pop sounds
│   ├── Pop2.mp3
│   ├── Pop3.mp3
│   └── lvup.mp3      # Level up sound
├── backgrounds/      # Ambient/background audio
├── startle_videos/   # Mandatory videos (MP4, AVI, MOV)
└── sub_audio/        # Subliminal whisper audio
```

### Supported Formats

| Folder | Formats |
|--------|---------|
| images | PNG, JPG, JPEG, GIF, BMP, WEBP |
| sounds | MP3, WAV, OGG |
| startle_videos | MP4, AVI, MOV, MKV, WEBM |
| sub_audio | MP3, WAV, OGG |
| backgrounds | MP3, WAV, OGG |

---

## ⚠️ Safety & Warnings

### ⚡ Panic Key
**ESC** immediately stops all effects and returns control. This is your safety net!

### 🔴 The Danger Combination

**DO NOT** enable all of these at once unless you know what you're doing:

| Setting | Risk |
|---------|------|
| ✅ Strict Lock | Cannot close video |
| ✅ ⚠️ No Panic | ESC key disabled |
| ✅ Start Hidden | App starts invisible |
| ✅ Win Start | Runs on Windows boot |

**If all enabled:** You will lose control until:
1. Video completes
2. You fail 3 attention checks (Mercy System)
3. You hard-reboot your computer

### 🛡️ Mercy System

If you fail the attention mini-game 3 times in a row:
1. "DUMB BAMBI" penalty screen appears
2. After the penalty, you're released
3. Counter resets

This prevents being permanently stuck.

### 💡 Safe Practices

1. **Test settings first** - Try without Strict Lock
2. **Keep ESC enabled** - Only disable if you're sure
3. **Start with Beginner preset** - Work your way up
4. **Use Time Schedule** - Limit when effects can trigger
5. **Keep task manager accessible** - Just in case

---

## 🔧 Troubleshooting

### Browser Not Loading
- Ensure Google Chrome is installed
- Try: `pip install --upgrade webdriver-manager selenium`
- Check if Chrome and chromedriver versions match

### Audio Ducking Not Working
- Run the application as Administrator
- Install: `pip install pycaw comtypes`
- Some apps (games, protected processes) can't be ducked

### Bubbles Not Appearing
- Check you're Level 20+ (see header bar)
- Enable "Bubbles" in Progression tab
- Ensure `assets/images/bubble.png` exists
- Bubbles don't spawn during flashes

### Bubbles Not Clickable
- Fixed in v2.0 - entire area should be clickable
- Try restarting the application

### High CPU Usage
- Reduce "Max On Screen" images
- Disable Spiral overlay
- Lower bubble frequency
- The app auto-throttles when system is loaded

### Flash Images Keep Spawning Forever
- Fixed in v2.0 - auto-cleanup after audio ends
- Corruption mode is now properly limited

### Videos Won't Play
- Check video format (MP4 recommended)
- Ensure video isn't corrupted
- Try converting with HandBrake

### Application Won't Start
- Delete `settings.json` to reset configuration
- Check for Python errors in console
- Ensure all dependencies are installed

### Spiral Not Showing
- Unlock at Level 10
- Select a spiral file (GIF or video)
- Increase opacity if too faint

---

## ⌨️ Keyboard Shortcuts

| Key | Action |
|-----|--------|
| **ESC** | Panic Stop - immediately halts everything |

*(More shortcuts planned for future versions)*

---

## ❓ FAQ

### Q: How do I reset everything?
**A:** Delete `settings.json` in the app folder. Next launch will be fresh.

### Q: Can I use this on Mac/Linux?
**A:** Currently Windows-only due to pycaw (audio ducking) and window management APIs.

### Q: How do I add my own images?
**A:** Put PNG/JPG/GIF files in the `assets/images/` folder.

### Q: What size should images be?
**A:** Any size works - they're automatically scaled. 800x600 to 1920x1080 is ideal.

### Q: Can I use videos as flash images?
**A:** Flash images support GIF animations. For full videos, use the `startle_videos` folder.

### Q: How do I create a spiral?
**A:** Use any looping GIF or video. Many are available online, or create with video editors.

### Q: Is my progress saved?
**A:** Yes! Level and XP save automatically to `settings.json`.

### Q: How do I backup my settings?
**A:** Copy `settings.json` and `presets.json` to a safe location.

### Q: Can I run multiple instances?
**A:** No, the app uses a single-instance lock to prevent conflicts.

### Q: Why do bubbles disappear when video starts?
**A:** Performance optimization - bubbles auto-pop to free resources for video playback.

### Q: The welcome screen keeps showing
**A:** Delete `settings.json` or ensure `"welcomed": true` is in the file.

---

## 🎀 Credits

Built with 💕 for the community.

**Technologies:**
- CustomTkinter - Modern Python UI
- Pillow - Image processing
- Pygame - Audio playback
- OpenCV - Video playback
- Selenium - Embedded browser
- Pycaw - Windows audio control

---

## 📜 Disclaimer

This software is for personal use only. Users are responsible for:
- Their own experience and wellbeing
- Content added to asset folders
- Understanding the risks of Strict Lock mode
- Using the application responsibly

The developers are not responsible for any misuse or unintended effects.

---

*Enjoy the pink fog.* 🎀

**Version 2.0** | [CHANGELOG.md](CHANGELOG.md)
