# Changelog - Conditioning Control Panel

## Version 2.1.0 (Security Update) - 2025-01

### 🔒 Security Overhaul
- **NEW: security.py** - Centralized security module with:
  - File-based logging with rotation (`logs/app.log`)
  - Path validation and sanitization (prevents directory traversal)
  - Settings validation schema
  - Dangerous settings detection and warnings
- **Exception Handling**: Fixed **91 bare `except:` clauses** across all modules
  - All exceptions now catch specific types (e.g., `tk.TclError`, `pygame.error`)
  - Better error context logged for debugging
- **Input Validation**: Settings validated on load against schema
- **Version System**: Added version constants and tracking

### 📦 Build Improvements
- **Updated build_app.py**:
  - Version number in output filename
  - Excludes unnecessary modules to reduce size
  - Better asset filtering (removes .psd, .bak, etc.)
  - Verbose mode support (`VERBOSE=1`)
- **NEW: installer.iss** - Inno Setup script for professional Windows installer
- **Cleaner exe name**: `ConditioningControlPanel.exe` (no spaces)

### 🎨 Polish
- Window title shows version number
- Startup logging with version info
- Dangerous settings logged on load

### 🐛 Bug Fixes
- Fixed `main.py` importing wrong class name (`ControlPanel` not `ConditioningApp`)

---

## Version 2.0.1 (Hotfix) - 2025-01

### 🐛 Bug Fixes
- **Volume Curve**: Changed from `vol²` to `vol^1.5` with 5% minimum
  - 20% slider now produces audible volume (was silent before)
  - Applied to: video audio, flash sounds, subliminal audio, bubble pops
- **Welcome Dialog**: Now appears ON TOP of browser window
  - Added `topmost` attribute and delayed lift
  - Adjusted timing: welcome at 1500ms, auto-start at 2000ms
- **Video Limit**: Reduced max videos per hour from 60 to 20
  - Prevents excessive interruption
- **Level-Up Sound**: Added `assets/sounds/lvup.mp3` requirement

---

## Version 2.0 (Major Refactor)

### 🏗️ Architecture Changes
- **Modular Codebase**: Split monolithic `Conditioning_Control_Panel_1_1.py` into separate modules:
  - `main.py` - Entry point
  - `config.py` - Configuration and default settings
  - `engine.py` - Core flash/video/subliminal engine
  - `gui.py` - Modern UI with CustomTkinter
  - `browser.py` - Embedded browser manager
  - `utils.py` - Utilities (audio ducking, single instance)
  - `ui_components.py` - Reusable UI components
  - `progression_system.py` - XP, levels, and unlockables
  - `bubble_game.py` - Bubble pop mini-game
  - `Overlay_spiral.py` - Spiral overlay effect

### 🎀 Welcome Experience
- **First Launch Welcome**: New users see a welcome dialog explaining the app
- **Built-in Presets**: Four preset difficulty levels:
  - 🌸 **Beginner Bimbo** - Low intensity, perfect for starting
  - 💄 **Bimbo in Training** - Medium-low, gentle conditioning
  - 💋 **Advanced Bimbo** - Medium-high, more intense
  - 👑 **Ultimate Bimbodoll** - High intensity experience
- **Preset Menu**: All presets available in dropdown menu anytime

### 🎨 UI Redesign
- **Modern Dark Theme**: Hot pink accents (#FF69B4) with purple backgrounds (#1A0A1F)
- **Compact Layout**: 3-column grid (Controls | Settings | Browser)
- **Comprehensive Tooltips**: Every control has detailed explanations
- **Clearer Labels**: Renamed confusing options for clarity
- **Tab System**: Settings and Progression tabs with segmented buttons
- **XP Bar**: Integrated into header with level display
- **Browser Panel**: Embedded with themed header bar covering Chrome controls

### ⚡ Performance Optimizations
- **Global ResourceManager**: Singleton tracking all active effects with load-based throttling
- **Pre-loaded Assets**: Bubble images loaded at startup to prevent white flash
- **Spiral Optimization**: Reduced to 12 FPS, 24 frames, 1280x720 resolution
- **Rate Limiting**: Minimum 0.5s between effect starts
- **Reduced Concurrent Effects**: Max 4 bubbles, 15 flashes
- **Video Preparation**: 4-second delay before video starts to free resources
- **Aggressive Cleanup**: Better memory management on stop

### 🎮 Progression System
- **XP Formula**: 50 + (level × 20) per level - faster progression
- **Level Unlocks**:
  - Level 10: Spiral Overlay, Pink Filter
  - Level 20: Bubble Pop Game
  - Level 50+: Coming soon
- **Level Up Sound**: Plays `lvup.mp3` on level up

### 🫧 Bubble Game Improvements
- **Fixed Hitbox**: Separate invisible click-catcher window (entire bubble area is clickable)
- **Multi-Monitor Support**: Bubbles spawn on random monitors
- **Resource Tracking**: Registers with ResourceManager
- **Pop All on Stop**: All bubbles pop (with sounds) when stopping/closing
- **Video Awareness**: Bubbles auto-pop when video starts

### 🔄 Flash/Bubble Coordination
- **Mutual Exclusion**: Flashes wait for bubbles to clear, bubbles wait for flashes
- **ResourceManager Tracking**: Real-time count of active effects
- **Flash Waiting State**: Prevents bubble spawn during flash wait
- **Video Priority**: Both effects clear immediately when video triggered

### 📺 Flash Images
- **Separate Controls**:
  - `Clickable`: ON = click to close, OFF = ghost mode (click-through)
  - `💀 Corruption`: ON = hydra effect (close 1 → spawn 2), OFF = just closes
- **Linked Sliders**: "Max On Screen" automatically stays ≥ "Images" count
- **Hard Cap**: Maximum 20 images on screen (prevents system overload)
- **Audio Ducking**: Now ducks even without sound file
- **Auto-Cleanup**: Images fade out 1 second after audio ends (stops hydra forever-spawn)

### 🔊 Audio Improvements
- **Volume Reduction**: All sounds reduced to prevent ear fatigue
- **Proper Ducking**: Audio ducking now works on all flashes (not just those with sound)
- **Unduck Timing**: Properly schedules unduck after effect completion

### 🎬 Video (Startle) Updates
- **4-Second Preparation Delay**: Video starts 4 seconds after trigger for:
  - Bubble cleanup with sounds
  - Spiral pause/hide
  - Flash window cleanup
  - Audio stop
  - Resource freeing
- **Video Pending State**: ResourceManager tracks pending videos
- **Spiral Management**: Completely stops spiral during video (not just pause)
- **Proper Cleanup**: Better video resource cleanup

### 💬 Subliminals
- **Audio Whispers**: Optional audio from `sub_audio` folder
- **Style Editor**: Customize colors and transparency

### ⏱️ Scheduler
- **Intensity Ramp**: Gradually increases intensity over configurable duration
- **Time Schedule**: Run only during specific hours/days
- **Link Opacity**: Option to increase opacity with intensity

### 🛡️ Safety Features
- **Panic Key**: ESC stops everything (can be disabled)
- **Strict Lock Warning**: Danger indicators on risky settings
- **Mercy Counter**: 3 failed attention checks releases lock

### 🐛 Bug Fixes
- Fixed bubble click detection (was only working on non-transparent pixels)
- Fixed flash/bubble overlap conflicts
- Fixed hydra mode exceeding max images limit
- Fixed hydra mode spawning forever after audio ends
- Fixed slider labels not updating
- Fixed browser not loading
- Fixed audio ducking not triggering on flashes
- Fixed bubbles continuing to spawn during flashes
- Fixed bubbles not popping on program close
- Fixed system freezing when multiple effects overlap
- Fixed spiral not stopping during video playback

---

## Version 1.1 (Original)
- Single-file implementation
- Basic flash, subliminal, and startle functionality
- Attention game during videos
- Audio ducking support
- Dual monitor support
