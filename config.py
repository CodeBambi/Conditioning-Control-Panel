import os
import sys

# --- PATHS ---
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

ASSETS_DIR = os.path.join(BASE_DIR, "assets")
IMG_DIR = os.path.join(ASSETS_DIR, "images")
SND_DIR = os.path.join(ASSETS_DIR, "sounds")
SUB_AUDIO_DIR = os.path.join(ASSETS_DIR, "sub_audio")
STARTLE_VID_DIR = os.path.join(ASSETS_DIR, "startle_videos")

SETTINGS_FILE = os.path.join(BASE_DIR, "settings.json")
PRESETS_FILE = os.path.join(BASE_DIR, "presets.json")
TEMP_AUDIO_FILE = os.path.join(ASSETS_DIR, "temp_spot_audio.wav")

# Browser Profile for Persistent Cookies
BROWSER_PROFILE_DIR = os.path.join(BASE_DIR, "BambiBrowserData")
BAMBI_URL = "https://bambicloud.com/"

STARTUP_FOLDER = os.path.join(os.getenv('APPDATA'), r'Microsoft\Windows\Start Menu\Programs\Startup')
STARTUP_FILE_NAME = "ConditioningApp_AutoRun.bat"
STARTUP_FILE_PATH = os.path.join(STARTUP_FOLDER, STARTUP_FILE_NAME)

# --- THEME ---
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

# --- TEXT POOL ---
BAMBI_TEXT_LIST = [
    "BAMBI FREEZE", "BAMBI RESET", "BAMBI SLEEP", "BAMBI UNIFORM LOCK",
    "BIMBO DOLL", "COCK ZOMBIE NOW", "DROP FOR COCK", "GIGGLETIME",
    "GOOD GIRL", "ZAP COCK DRAIN OBEY"
]
BAMBI_POOL_DICT = {text: True for text in BAMBI_TEXT_LIST}

# --- XP SYSTEM ---
# New formula: XP needed = 50 + (level * 20)
# Total XP for levels 1-20: ~4,700 XP
# At low settings (~10 XP/min): ~8 hours to level 20
# At medium settings (~20 XP/min): ~4 hours to level 20
def xp_for_level(level):
    """Calculate XP needed for the next level"""
    return 50 + (level * 20)

# --- DEFAULT SETTINGS ---
DEFAULT_SETTINGS = {
    "player_level": 1,
    "player_xp": 0.0,
    "welcomed": False,  # Track if user has seen welcome message
    
    # Flash settings - streamlined with frequency slider
    "flash_enabled": True,
    "flash_freq": 2,  # Flashes per minute (1-10)
    "flash_clickable": True,
    "flash_corruption": False,  # Hydra effect - clicking spawns 2 more
    "flash_hydra_limit": 20,  # Max images on screen (capped at 20)
    "sim_images": 5,  # Number of images per flash (1-10)
    "image_scale": 0.9,
    "image_alpha": 1.0,
    "fade_duration": 0.4,
    
    # Startle/Video settings
    "startle_enabled": True,
    "startle_freq": 6,
    "startle_strict": False,
    "force_startle_on_launch": False,
    
    # Audio - reduced by 20%
    "volume": 0.32,  # Was 0.4, now 20% lower
    
    # System
    "dual_monitor": True,
    "run_on_startup": False,
    "start_minimized": False,
    "auto_start_engine": False,
    "last_preset": "DEFAULT",
    "disable_panic_esc": False,
    
    # Subliminals - max 30/min
    "subliminal_enabled": False,
    "subliminal_freq": 5,  # Max slider will be 30
    "subliminal_duration": 2,
    "subliminal_opacity": 0.8,
    "subliminal_pool": BAMBI_POOL_DICT.copy(),
    "sub_bg_color": "#000000",
    "sub_bg_transparent": False,
    "sub_text_color": "#FF00FF",
    "sub_text_transparent": False,
    "sub_border_color": "#FFFFFF",
    "sub_audio_enabled": False,
    "sub_audio_volume": 0.5,
    
    # Background audio
    "bg_audio_enabled": True,
    "bg_audio_max": 15,
    "audio_ducking_enabled": True,
    "audio_ducking_strength": 100,
    
    # Attention mini-game - max 20 targets
    "attention_enabled": False,
    "attention_density": 3,  # Max slider will be 20
    "attention_lifespan": 5,
    "attention_size": 70,
    "attention_pool": BAMBI_POOL_DICT.copy(),
    
    # Scheduler/Ramping
    "scheduler_enabled": False,
    "scheduler_duration_min": 60,
    "scheduler_multiplier": 1.0,
    "scheduler_link_alpha": False,
    "time_schedule_enabled": False,
    "time_start_str": "16:00",
    "time_end_str": "18:00",
    "active_weekdays": [0, 1, 2, 3, 4, 5, 6],
    
    # Spiral overlay
    "spiral_enabled": False,
    "spiral_path": "",
    "spiral_opacity": 0.10,
    "spiral_link_ramp": False,

    # Bubbles
    "bubbles_enabled": False,
    "bubbles_freq": 5,
    "bubbles_link_ramp": False,

    # Pink filter
    "pink_filter_enabled": False,
    "pink_filter_opacity": 0.10,
    "pink_filter_link_ramp": False,
}
