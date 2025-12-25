"""
Configuration Module for Conditioning Control Panel
====================================================
Provides:
- Path definitions
- Theme settings
- Default configuration values
- XP calculation
"""

import os
import sys

# =============================================================================
# PATH CONFIGURATION
# =============================================================================

def get_base_dir() -> str:
    """Get the base directory of the application."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

BASE_DIR = get_base_dir()

# Asset directories
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
IMG_DIR = os.path.join(ASSETS_DIR, "images")
SND_DIR = os.path.join(ASSETS_DIR, "sounds")
SUB_AUDIO_DIR = os.path.join(ASSETS_DIR, "sub_audio")
STARTLE_VID_DIR = os.path.join(ASSETS_DIR, "startle_videos")

# Config files
SETTINGS_FILE = os.path.join(BASE_DIR, "settings.json")
PRESETS_FILE = os.path.join(BASE_DIR, "presets.json")
TEMP_AUDIO_FILE = os.path.join(ASSETS_DIR, "temp_spot_audio.wav")

# Browser Profile for Persistent Cookies
BROWSER_PROFILE_DIR = os.path.join(BASE_DIR, "BambiBrowserData")
BAMBI_URL = "https://bambicloud.com/"

# Windows startup folder (optional feature)
STARTUP_FOLDER = os.path.join(os.getenv('APPDATA', ''), r'Microsoft\Windows\Start Menu\Programs\Startup')
STARTUP_FILE_NAME = "ConditioningApp_AutoRun.bat"
STARTUP_FILE_PATH = os.path.join(STARTUP_FOLDER, STARTUP_FILE_NAME)


# =============================================================================
# THEME CONFIGURATION
# =============================================================================

THEME = {
    "bg": "#FF69B4",
    "header_bg": "#C51162",
    "card_bg": "#FFE4E1",
    "fg": "#4B0082",
    "fg_sub": "#880E4F",
    "font_family": "Segoe UI",
    "btn_bg": "#D500F9",
    "btn_hover": "#AA00FF",
    "accent": "#FF4081",
    "warning": "#D32F2F",
    "entry_bg": "#FFFFFF",
    "entry_text": "#4A148C",
    "tooltip_bg": "#F8BBD0",
    "tooltip_fg": "#880E4F",
    "list_select": "#E1BEE7",
    "xp_bar": "#FF00CC",
    "xp_bg": "#880E4F"
}


# =============================================================================
# SUBLIMINAL TEXT POOL
# =============================================================================

BAMBI_TEXT_LIST = [
    "BAMBI FREEZE", "BAMBI RESET", "BAMBI SLEEP", "BAMBI UNIFORM LOCK",
    "BIMBO DOLL", "COCK ZOMBIE NOW", "DROP FOR COCK", "GIGGLETIME",
    "GOOD GIRL", "ZAP COCK DRAIN OBEY"
]
BAMBI_POOL_DICT = {text: True for text in BAMBI_TEXT_LIST}


# =============================================================================
# XP SYSTEM
# =============================================================================

def xp_for_level(level: int) -> int:
    """
    Calculate XP needed for the next level.
    
    Formula: 50 + (level * 20)
    
    Args:
        level: Current level
    
    Returns:
        XP required to reach next level
    
    Examples:
        Level 1→2: 70 XP
        Level 10→11: 250 XP
        Level 20→21: 450 XP
    
    Total XP for levels 1-20: ~4,700 XP
    At low settings (~10 XP/min): ~8 hours to level 20
    At medium settings (~20 XP/min): ~4 hours to level 20
    """
    if not isinstance(level, int) or level < 1:
        level = 1
    return 50 + (level * 20)


# =============================================================================
# DEFAULT SETTINGS
# =============================================================================

DEFAULT_SETTINGS = {
    # --- Player Progress ---
    "player_level": 1,
    "player_xp": 0.0,
    "welcomed": False,
    
    # --- Flash Images ---
    "flash_enabled": True,
    "flash_freq": 2,           # Flashes per minute (1-10)
    "flash_clickable": True,
    "flash_corruption": False,  # Hydra effect
    "flash_hydra_limit": 20,    # Max images on screen (hard cap: 20)
    "sim_images": 5,            # Images per flash (1-20)
    "image_scale": 0.9,         # 50-250%
    "image_alpha": 1.0,         # 10-100%
    "fade_duration": 0.4,       # 0-2 seconds
    
    # --- Mandatory Videos ---
    "startle_enabled": True,
    "startle_freq": 6,          # Videos per hour (1-20)
    "startle_strict": False,    # DANGEROUS: Cannot close video
    "force_startle_on_launch": False,
    
    # --- Audio ---
    "volume": 0.32,             # Master volume (0-100%)
    "audio_ducking_enabled": True,
    "audio_ducking_strength": 100,
    
    # --- System ---
    "dual_monitor": True,
    "run_on_startup": False,
    "start_minimized": False,
    "auto_start_engine": False,
    "last_preset": "DEFAULT",
    "disable_panic_esc": False,  # DANGEROUS: Disables ESC panic key
    
    # --- Subliminals ---
    "subliminal_enabled": False,
    "subliminal_freq": 5,       # Messages per minute (1-30)
    "subliminal_duration": 2,   # Frames (1-10)
    "subliminal_opacity": 0.8,
    "subliminal_pool": BAMBI_POOL_DICT.copy(),
    "sub_bg_color": "#000000",
    "sub_bg_transparent": False,
    "sub_text_color": "#FF00FF",
    "sub_text_transparent": False,
    "sub_border_color": "#FFFFFF",
    "sub_audio_enabled": False,
    "sub_audio_volume": 0.5,
    
    # --- Background Audio ---
    "bg_audio_enabled": True,
    "bg_audio_max": 15,
    
    # --- Attention Mini-game ---
    "attention_enabled": False,
    "attention_density": 3,     # Target count (1-10)
    "attention_lifespan": 5,
    "attention_size": 70,
    "attention_pool": BAMBI_POOL_DICT.copy(),
    
    # --- Scheduler ---
    "scheduler_enabled": False,
    "scheduler_duration_min": 60,
    "scheduler_multiplier": 1.0,
    "scheduler_link_alpha": False,
    "time_schedule_enabled": False,
    "time_start_str": "16:00",
    "time_end_str": "18:00",
    "active_weekdays": [0, 1, 2, 3, 4, 5, 6],
    
    # --- Spiral Overlay (Unlocks Lv.10) ---
    "spiral_enabled": False,
    "spiral_path": "",
    "spiral_opacity": 0.10,
    "spiral_link_ramp": False,

    # --- Bubbles (Unlocks Lv.20) ---
    "bubbles_enabled": False,
    "bubbles_freq": 5,
    "bubbles_link_ramp": False,

    # --- Pink Filter (Unlocks Lv.10) ---
    "pink_filter_enabled": False,
    "pink_filter_opacity": 0.10,
    "pink_filter_link_ramp": False,
}


# =============================================================================
# SAFETY LIMITS
# =============================================================================

# Hard limits that cannot be exceeded
LIMITS = {
    "max_images_on_screen": 20,
    "max_videos_per_hour": 20,
    "max_bubbles": 8,
    "max_flashes_per_min": 10,
    "max_subliminals_per_min": 30,
    "max_attention_targets": 10,
}


def validate_limits(settings: dict) -> dict:
    """
    Ensure settings don't exceed safety limits.
    
    Args:
        settings: Settings dictionary to validate
    
    Returns:
        Settings with values clamped to limits
    """
    if not isinstance(settings, dict):
        return DEFAULT_SETTINGS.copy()
    
    validated = settings.copy()
    
    # Clamp values to limits
    if validated.get('flash_hydra_limit', 0) > LIMITS['max_images_on_screen']:
        validated['flash_hydra_limit'] = LIMITS['max_images_on_screen']
    
    if validated.get('sim_images', 0) > LIMITS['max_images_on_screen']:
        validated['sim_images'] = LIMITS['max_images_on_screen']
    
    if validated.get('startle_freq', 0) > LIMITS['max_videos_per_hour']:
        validated['startle_freq'] = LIMITS['max_videos_per_hour']
    
    if validated.get('flash_freq', 0) > LIMITS['max_flashes_per_min']:
        validated['flash_freq'] = LIMITS['max_flashes_per_min']
    
    if validated.get('subliminal_freq', 0) > LIMITS['max_subliminals_per_min']:
        validated['subliminal_freq'] = LIMITS['max_subliminals_per_min']
    
    if validated.get('attention_density', 0) > LIMITS['max_attention_targets']:
        validated['attention_density'] = LIMITS['max_attention_targets']
    
    return validated
