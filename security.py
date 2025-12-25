"""
Security and Logging Module for Conditioning Control Panel
===========================================================
Provides:
- Centralized logging with rotation
- Input validation and sanitization
- Path safety checks
- Settings validation schema
"""

import os
import re
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
from typing import Any, Dict, Optional, Union, List

# =============================================================================
# LOGGING SETUP
# =============================================================================

LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
LOG_FILE = os.path.join(LOG_DIR, "app.log")
MAX_LOG_SIZE = 5 * 1024 * 1024  # 5 MB
BACKUP_COUNT = 3

def setup_logging(level: int = logging.INFO) -> logging.Logger:
    """
    Set up centralized logging with file rotation.
    
    Args:
        level: Logging level (default INFO)
    
    Returns:
        Configured logger instance
    """
    # Create logs directory if it doesn't exist
    if not os.path.exists(LOG_DIR):
        try:
            os.makedirs(LOG_DIR)
        except OSError as e:
            print(f"Warning: Could not create log directory: {e}")
            # Fall back to console-only logging
            logging.basicConfig(level=level)
            return logging.getLogger("ConditioningPanel")
    
    # Create logger
    logger = logging.getLogger("ConditioningPanel")
    logger.setLevel(level)
    
    # Avoid duplicate handlers
    if logger.handlers:
        return logger
    
    # File handler with rotation
    try:
        file_handler = RotatingFileHandler(
            LOG_FILE,
            maxBytes=MAX_LOG_SIZE,
            backupCount=BACKUP_COUNT,
            encoding='utf-8'
        )
        file_handler.setLevel(level)
        file_format = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(module)s:%(lineno)d | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_format)
        logger.addHandler(file_handler)
    except (OSError, IOError) as e:
        print(f"Warning: Could not create log file: {e}")
    
    # Console handler (less verbose)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)
    console_format = logging.Formatter('%(levelname)s: %(message)s')
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)
    
    logger.info("=" * 60)
    logger.info(f"Application started at {datetime.now().isoformat()}")
    logger.info("=" * 60)
    
    return logger


# Global logger instance
logger = setup_logging()


# =============================================================================
# PATH SECURITY
# =============================================================================

# Allowed base directories (relative to app root)
ALLOWED_ASSET_DIRS = {'assets', 'presets', 'logs'}

# Allowed file extensions by category
ALLOWED_EXTENSIONS = {
    'images': {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'},
    'sounds': {'.mp3', '.wav', '.ogg'},
    'videos': {'.mp4', '.avi', '.mov', '.mkv', '.webm'},
    'config': {'.json'},
    'spiral': {'.gif', '.mp4', '.avi', '.mov', '.webp'},
}


def get_app_root() -> str:
    """Get the application root directory."""
    return os.path.dirname(os.path.abspath(__file__))


def is_safe_path(filepath: str, allowed_dirs: Optional[set] = None) -> bool:
    """
    Check if a file path is safe (no directory traversal).
    
    Args:
        filepath: Path to validate
        allowed_dirs: Set of allowed base directories (default: ALLOWED_ASSET_DIRS)
    
    Returns:
        True if path is safe, False otherwise
    """
    if not filepath:
        return False
    
    if allowed_dirs is None:
        allowed_dirs = ALLOWED_ASSET_DIRS
    
    # Normalize the path
    try:
        filepath = os.path.normpath(filepath)
    except (TypeError, ValueError) as e:
        logger.warning(f"Invalid path format: {filepath} - {e}")
        return False
    
    # Check for directory traversal attempts
    if '..' in filepath or filepath.startswith('/') or filepath.startswith('\\'):
        # Allow absolute paths only if they're within the app directory
        app_root = get_app_root()
        try:
            abs_path = os.path.abspath(filepath)
            if not abs_path.startswith(app_root):
                logger.warning(f"Path traversal attempt blocked: {filepath}")
                return False
        except (TypeError, ValueError):
            logger.warning(f"Could not resolve absolute path: {filepath}")
            return False
    
    return True


def sanitize_path(filepath: str, base_dir: str = "assets") -> Optional[str]:
    """
    Sanitize a file path, ensuring it stays within allowed directories.
    
    Args:
        filepath: Raw file path
        base_dir: Base directory to resolve relative to
    
    Returns:
        Sanitized absolute path, or None if invalid
    """
    if not filepath:
        return None
    
    try:
        # Remove any null bytes (security risk)
        filepath = filepath.replace('\x00', '')
        
        # Normalize path separators
        filepath = filepath.replace('/', os.sep).replace('\\', os.sep)
        
        # Get app root
        app_root = get_app_root()
        
        # If it's already absolute, verify it's within app directory
        if os.path.isabs(filepath):
            abs_path = os.path.normpath(filepath)
            if not abs_path.startswith(app_root):
                logger.warning(f"Path outside app directory rejected: {filepath}")
                return None
            return abs_path
        
        # Make it absolute relative to base_dir
        full_path = os.path.normpath(os.path.join(app_root, base_dir, filepath))
        
        # Verify it's still within the app directory
        if not full_path.startswith(app_root):
            logger.warning(f"Path traversal blocked: {filepath} resolved to {full_path}")
            return None
        
        return full_path
        
    except (TypeError, ValueError, OSError) as e:
        logger.error(f"Path sanitization failed for '{filepath}': {e}")
        return None


def validate_file_extension(filepath: str, category: str) -> bool:
    """
    Validate that a file has an allowed extension for its category.
    
    Args:
        filepath: Path to the file
        category: Category name (images, sounds, videos, config, spiral)
    
    Returns:
        True if extension is allowed, False otherwise
    """
    if not filepath or category not in ALLOWED_EXTENSIONS:
        return False
    
    ext = os.path.splitext(filepath)[1].lower()
    allowed = ALLOWED_EXTENSIONS.get(category, set())
    
    if ext not in allowed:
        logger.warning(f"Invalid file extension '{ext}' for category '{category}': {filepath}")
        return False
    
    return True


# =============================================================================
# INPUT VALIDATION
# =============================================================================

# Settings schema: key -> (type, min, max, default)
SETTINGS_SCHEMA = {
    # Player progress
    "player_level": (int, 1, 999, 1),
    "player_xp": (float, 0, 999999, 0.0),
    "welcomed": (bool, None, None, False),
    
    # Flash settings
    "flash_enabled": (bool, None, None, True),
    "flash_freq": (int, 1, 10, 2),
    "flash_clickable": (bool, None, None, True),
    "flash_corruption": (bool, None, None, False),
    "flash_hydra_limit": (int, 1, 20, 20),
    "sim_images": (int, 1, 20, 5),
    "image_scale": (float, 0.5, 2.5, 0.9),
    "image_alpha": (float, 0.1, 1.0, 1.0),
    "fade_duration": (float, 0.0, 2.0, 0.4),
    
    # Video settings
    "startle_enabled": (bool, None, None, True),
    "startle_freq": (int, 1, 20, 6),
    "startle_strict": (bool, None, None, False),
    "attention_enabled": (bool, None, None, False),
    "attention_density": (int, 1, 10, 3),
    
    # Subliminal settings
    "subliminal_enabled": (bool, None, None, False),
    "subliminal_freq": (int, 1, 30, 5),
    "subliminal_duration": (int, 1, 10, 2),
    "subliminal_opacity": (float, 0.1, 1.0, 0.7),
    "sub_audio_enabled": (bool, None, None, False),
    "sub_audio_volume": (float, 0.0, 1.0, 0.5),
    
    # Audio settings
    "volume": (float, 0.0, 1.0, 0.5),
    "audio_ducking_enabled": (bool, None, None, True),
    "audio_ducking_strength": (int, 0, 100, 80),
    
    # Progression settings
    "pink_filter_enabled": (bool, None, None, False),
    "pink_filter_opacity": (float, 0.05, 0.5, 0.1),
    "pink_filter_link_ramp": (bool, None, None, False),
    "spiral_enabled": (bool, None, None, False),
    "spiral_opacity": (float, 0.1, 1.0, 0.1),
    "spiral_link_ramp": (bool, None, None, False),
    "spiral_path": (str, None, None, ""),
    "bubbles_enabled": (bool, None, None, False),
    "bubbles_freq": (int, 1, 15, 5),
    "bubbles_link_ramp": (bool, None, None, False),
    
    # Scheduler settings
    "scheduler_enabled": (bool, None, None, False),
    "scheduler_duration_min": (int, 5, 120, 30),
    "scheduler_multiplier": (float, 1.0, 3.0, 1.5),
    
    # System settings
    "dual_monitor": (bool, None, None, False),
    "disable_panic_esc": (bool, None, None, False),
    "start_minimized": (bool, None, None, False),
    "auto_start_engine": (bool, None, None, False),
    "force_startle_on_launch": (bool, None, None, False),
    
    # Browser
    "browser_url": (str, None, None, "https://www.google.com"),
}


def validate_setting(key: str, value: Any) -> tuple[bool, Any]:
    """
    Validate a single setting value against the schema.
    
    Args:
        key: Setting key name
        value: Value to validate
    
    Returns:
        Tuple of (is_valid, sanitized_value)
    """
    if key not in SETTINGS_SCHEMA:
        # Unknown setting - allow but log
        logger.debug(f"Unknown setting key: {key}")
        return True, value
    
    expected_type, min_val, max_val, default = SETTINGS_SCHEMA[key]
    
    # Type check
    if expected_type == bool:
        if not isinstance(value, bool):
            logger.warning(f"Invalid type for {key}: expected bool, got {type(value).__name__}")
            return False, default
    elif expected_type == int:
        if not isinstance(value, (int, float)):
            logger.warning(f"Invalid type for {key}: expected int, got {type(value).__name__}")
            return False, default
        value = int(value)
    elif expected_type == float:
        if not isinstance(value, (int, float)):
            logger.warning(f"Invalid type for {key}: expected float, got {type(value).__name__}")
            return False, default
        value = float(value)
    elif expected_type == str:
        if not isinstance(value, str):
            logger.warning(f"Invalid type for {key}: expected str, got {type(value).__name__}")
            return False, default
    
    # Range check for numeric types
    if expected_type in (int, float) and min_val is not None and max_val is not None:
        if value < min_val:
            logger.warning(f"Value {value} for {key} below minimum {min_val}, clamping")
            value = min_val
        elif value > max_val:
            logger.warning(f"Value {value} for {key} above maximum {max_val}, clamping")
            value = max_val
    
    return True, value


def validate_settings(settings: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate and sanitize an entire settings dictionary.
    
    Args:
        settings: Raw settings dictionary
    
    Returns:
        Sanitized settings dictionary with invalid values replaced by defaults
    """
    if not isinstance(settings, dict):
        logger.error(f"Settings must be a dictionary, got {type(settings).__name__}")
        return get_default_settings()
    
    validated = {}
    
    for key, value in settings.items():
        is_valid, sanitized = validate_setting(key, value)
        validated[key] = sanitized
    
    # Add missing keys with defaults
    for key, (_, _, _, default) in SETTINGS_SCHEMA.items():
        if key not in validated:
            validated[key] = default
    
    logger.info(f"Settings validated: {len(validated)} keys")
    return validated


def get_default_settings() -> Dict[str, Any]:
    """Get a dictionary of all default settings."""
    return {key: default for key, (_, _, _, default) in SETTINGS_SCHEMA.items()}


# =============================================================================
# STRING SANITIZATION
# =============================================================================

def sanitize_string(text: str, max_length: int = 1000, allow_newlines: bool = True) -> str:
    """
    Sanitize a string input.
    
    Args:
        text: Raw input string
        max_length: Maximum allowed length
        allow_newlines: Whether to allow newline characters
    
    Returns:
        Sanitized string
    """
    if not isinstance(text, str):
        return ""
    
    # Remove null bytes
    text = text.replace('\x00', '')
    
    # Remove control characters (except newlines if allowed)
    if allow_newlines:
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    else:
        text = re.sub(r'[\x00-\x1f\x7f]', '', text)
    
    # Truncate to max length
    if len(text) > max_length:
        logger.warning(f"String truncated from {len(text)} to {max_length} chars")
        text = text[:max_length]
    
    return text


def sanitize_url(url: str) -> Optional[str]:
    """
    Validate and sanitize a URL.
    
    Args:
        url: Raw URL string
    
    Returns:
        Sanitized URL or None if invalid
    """
    if not isinstance(url, str):
        return None
    
    url = url.strip()
    
    # Basic URL validation
    if not url:
        return None
    
    # Must start with http:// or https://
    if not url.startswith(('http://', 'https://')):
        logger.warning(f"URL missing protocol: {url}")
        # Add https:// by default
        url = 'https://' + url
    
    # Block potentially dangerous protocols
    dangerous = ['javascript:', 'data:', 'file:', 'vbscript:']
    for proto in dangerous:
        if proto in url.lower():
            logger.warning(f"Blocked dangerous URL protocol: {url}")
            return None
    
    # Basic length check
    if len(url) > 2048:
        logger.warning(f"URL too long: {len(url)} chars")
        return None
    
    return url


# =============================================================================
# SAFETY WARNINGS
# =============================================================================

def check_dangerous_settings(settings: Dict[str, Any]) -> List[str]:
    """
    Check for dangerous setting combinations and return warnings.
    
    Args:
        settings: Current settings dictionary
    
    Returns:
        List of warning messages
    """
    warnings = []
    
    strict_lock = settings.get('startle_strict', False)
    no_panic = settings.get('disable_panic_esc', False)
    start_hidden = settings.get('start_minimized', False)
    
    if strict_lock:
        warnings.append("⚠️ Strict Lock is ON - Videos cannot be closed")
    
    if no_panic:
        warnings.append("⚠️ Panic key (ESC) is DISABLED")
    
    if strict_lock and no_panic:
        warnings.append("🔴 DANGER: Strict Lock + No Panic = No escape except attention check!")
    
    if strict_lock and no_panic and start_hidden:
        warnings.append("🔴 EXTREME DANGER: Hidden start with no escape - USE AT OWN RISK!")
        logger.warning("User enabled dangerous combination: strict_lock + no_panic + start_hidden")
    
    return warnings


# =============================================================================
# SAFE FILE OPERATIONS
# =============================================================================

def safe_read_file(filepath: str, category: str = "config") -> Optional[str]:
    """
    Safely read a file with path validation.
    
    Args:
        filepath: Path to file
        category: File category for extension validation
    
    Returns:
        File contents or None if error
    """
    safe_path = sanitize_path(filepath, "")
    if not safe_path:
        return None
    
    if category and not validate_file_extension(safe_path, category):
        return None
    
    try:
        with open(safe_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        logger.debug(f"File not found: {safe_path}")
        return None
    except (IOError, OSError, UnicodeDecodeError) as e:
        logger.error(f"Error reading file {safe_path}: {e}")
        return None


def safe_write_file(filepath: str, content: str, category: str = "config") -> bool:
    """
    Safely write to a file with path validation.
    
    Args:
        filepath: Path to file
        content: Content to write
        category: File category for extension validation
    
    Returns:
        True if successful, False otherwise
    """
    safe_path = sanitize_path(filepath, "")
    if not safe_path:
        return False
    
    if category and not validate_file_extension(safe_path, category):
        return False
    
    try:
        # Ensure directory exists
        dir_path = os.path.dirname(safe_path)
        if dir_path and not os.path.exists(dir_path):
            os.makedirs(dir_path)
        
        with open(safe_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.debug(f"Successfully wrote to: {safe_path}")
        return True
        
    except (IOError, OSError) as e:
        logger.error(f"Error writing file {safe_path}: {e}")
        return False


def get_safe_files_in_directory(directory: str, category: str) -> List[str]:
    """
    Get list of files in a directory with safe path handling.
    
    Args:
        directory: Directory path
        category: File category for extension filtering
    
    Returns:
        List of safe absolute file paths
    """
    safe_dir = sanitize_path(directory, "")
    if not safe_dir or not os.path.isdir(safe_dir):
        return []
    
    allowed_exts = ALLOWED_EXTENSIONS.get(category, set())
    if not allowed_exts:
        return []
    
    files = []
    try:
        for filename in os.listdir(safe_dir):
            ext = os.path.splitext(filename)[1].lower()
            if ext in allowed_exts:
                full_path = os.path.join(safe_dir, filename)
                if os.path.isfile(full_path):
                    files.append(full_path)
    except (OSError, IOError) as e:
        logger.error(f"Error listing directory {safe_dir}: {e}")
    
    return files
