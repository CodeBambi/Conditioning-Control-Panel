"""
Utility Module for Conditioning Control Panel
=============================================
Provides:
- Single instance checker
- Audio ducking with proper error handling
- Safe file operations
"""

import os
import sys
import time
import ctypes
from typing import Optional

# Import logger from security module
try:
    from security import logger
except ImportError:
    import logging
    logger = logging.getLogger("ConditioningPanel")


# =============================================================================
# SINGLE INSTANCE CHECKER
# =============================================================================

class SingleInstanceChecker:
    """
    Ensures only one instance of the application runs at a time.
    Uses a mutex on Windows for reliability.
    """
    
    def __init__(self, app_name: str = "ConditioningControlPanel"):
        """
        Initialize the single instance checker.
        
        Args:
            app_name: Unique identifier for this application
        """
        self.app_name = app_name
        self.mutex = None
        self._is_single = None
    
    def is_single_instance(self) -> bool:
        """
        Check if this is the only running instance.
        
        Returns:
            True if this is the only instance, False otherwise
        """
        if self._is_single is not None:
            return self._is_single
        
        if sys.platform != 'win32':
            # On non-Windows, use a lock file approach
            self._is_single = self._check_lockfile()
            return self._is_single
        
        try:
            # Windows: Use a named mutex
            self.mutex = ctypes.windll.kernel32.CreateMutexW(
                None, 
                ctypes.c_bool(True), 
                ctypes.c_wchar_p(f"Global\\{self.app_name}_Mutex")
            )
            
            last_error = ctypes.windll.kernel32.GetLastError()
            
            # ERROR_ALREADY_EXISTS = 183
            if last_error == 183:
                logger.info("Another instance detected via mutex")
                self._is_single = False
            else:
                self._is_single = True
                
        except (OSError, AttributeError) as e:
            logger.warning(f"Could not create mutex: {e}")
            # Fall back to lock file
            self._is_single = self._check_lockfile()
        
        return self._is_single
    
    def _check_lockfile(self) -> bool:
        """Fallback lock file check for non-Windows systems."""
        lock_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            f".{self.app_name}.lock"
        )
        
        try:
            if os.path.exists(lock_file):
                # Check if the process is still running
                with open(lock_file, 'r') as f:
                    pid = int(f.read().strip())
                
                if self._is_process_running(pid):
                    return False
                else:
                    # Stale lock file
                    os.remove(lock_file)
            
            # Create lock file with our PID
            with open(lock_file, 'w') as f:
                f.write(str(os.getpid()))
            
            return True
            
        except (IOError, OSError, ValueError) as e:
            logger.warning(f"Lock file check failed: {e}")
            return True  # Assume we're the only instance
    
    def _is_process_running(self, pid: int) -> bool:
        """Check if a process with given PID is running."""
        if sys.platform == 'win32':
            try:
                kernel32 = ctypes.windll.kernel32
                handle = kernel32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
                if handle:
                    kernel32.CloseHandle(handle)
                    return True
            except (OSError, AttributeError):
                pass
            return False
        else:
            try:
                os.kill(pid, 0)
                return True
            except OSError:
                return False
    
    def cleanup(self):
        """Clean up resources on exit."""
        if self.mutex and sys.platform == 'win32':
            try:
                ctypes.windll.kernel32.ReleaseMutex(self.mutex)
                ctypes.windll.kernel32.CloseHandle(self.mutex)
            except (OSError, AttributeError):
                pass
        
        # Remove lock file if we created it
        lock_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            f".{self.app_name}.lock"
        )
        if os.path.exists(lock_file):
            try:
                with open(lock_file, 'r') as f:
                    pid = int(f.read().strip())
                if pid == os.getpid():
                    os.remove(lock_file)
            except (IOError, OSError, ValueError):
                pass


# =============================================================================
# AUDIO DUCKING
# =============================================================================

class AudioDucker:
    """
    Handles audio ducking (lowering volume of other applications).
    Uses Windows Core Audio API via pycaw.
    """
    
    def __init__(self):
        """Initialize the audio ducker."""
        self.available = False
        self.sessions = None
        self.original_volumes = {}
        self.is_ducked = False
        self.duck_amount = 0.8  # Default: reduce to 20% (duck by 80%)
        
        self._init_audio_api()
    
    def _init_audio_api(self):
        """Initialize the audio API."""
        try:
            from pycaw.pycaw import AudioUtilities, ISimpleAudioVolume
            from comtypes import CLSCTX_ALL
            
            self._AudioUtilities = AudioUtilities
            self._ISimpleAudioVolume = ISimpleAudioVolume
            self._CLSCTX_ALL = CLSCTX_ALL
            self.available = True
            logger.info("Audio ducking initialized successfully")
            
        except ImportError as e:
            logger.info(f"Audio ducking not available: {e}")
            self.available = False
        except Exception as e:
            logger.warning(f"Audio ducking initialization failed: {e}")
            self.available = False
    
    def set_duck_amount(self, strength: int):
        """
        Set the ducking strength.
        
        Args:
            strength: 0-100 (0 = no ducking, 100 = full mute)
        """
        # Clamp to valid range
        strength = max(0, min(100, strength))
        self.duck_amount = strength / 100.0
    
    def duck(self, strength: int = 80):
        """
        Lower the volume of other applications.
        
        Args:
            strength: 0-100 (0 = no ducking, 100 = full mute)
        """
        if not self.available or self.is_ducked:
            return
        
        # Set duck amount from strength
        self.set_duck_amount(strength)
        
        try:
            sessions = self._AudioUtilities.GetAllSessions()
            
            for session in sessions:
                try:
                    if session.Process is None:
                        continue
                    
                    # Skip our own process
                    if session.Process.pid == os.getpid():
                        continue
                    
                    volume = session._ctl.QueryInterface(self._ISimpleAudioVolume)
                    current_vol = volume.GetMasterVolume()
                    
                    # Store original volume
                    self.original_volumes[session.Process.pid] = current_vol
                    
                    # Calculate ducked volume
                    new_vol = current_vol * (1.0 - self.duck_amount)
                    volume.SetMasterVolume(max(0.0, new_vol), None)
                    
                except (AttributeError, OSError) as e:
                    # Session may have ended
                    continue
            
            self.is_ducked = True
            logger.debug(f"Ducked {len(self.original_volumes)} audio sessions")
            
        except Exception as e:
            logger.warning(f"Audio ducking failed: {e}")
    
    def unduck(self):
        """Restore the original volume of other applications."""
        if not self.available or not self.is_ducked:
            return
        
        try:
            sessions = self._AudioUtilities.GetAllSessions()
            
            for session in sessions:
                try:
                    if session.Process is None:
                        continue
                    
                    pid = session.Process.pid
                    
                    if pid in self.original_volumes:
                        volume = session._ctl.QueryInterface(self._ISimpleAudioVolume)
                        volume.SetMasterVolume(self.original_volumes[pid], None)
                        
                except (AttributeError, OSError):
                    continue
            
            self.original_volumes.clear()
            self.is_ducked = False
            logger.debug("Audio unducked")
            
        except Exception as e:
            logger.warning(f"Audio unducking failed: {e}")
            self.original_volumes.clear()
            self.is_ducked = False
    
    def cleanup(self):
        """Ensure audio is restored on exit."""
        if self.is_ducked:
            self.unduck()


# =============================================================================
# SAFE JSON OPERATIONS
# =============================================================================

def safe_load_json(filepath: str, default: Optional[dict] = None) -> dict:
    """
    Safely load a JSON file with error handling.
    
    Args:
        filepath: Path to JSON file
        default: Default value if file doesn't exist or is invalid
    
    Returns:
        Loaded dictionary or default value
    """
    import json
    
    if default is None:
        default = {}
    
    if not filepath or not os.path.exists(filepath):
        return default.copy() if isinstance(default, dict) else default
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if not isinstance(data, dict):
            logger.warning(f"JSON file {filepath} does not contain a dictionary")
            return default.copy() if isinstance(default, dict) else default
        
        return data
        
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in {filepath}: {e}")
        return default.copy() if isinstance(default, dict) else default
    except (IOError, OSError) as e:
        logger.error(f"Could not read {filepath}: {e}")
        return default.copy() if isinstance(default, dict) else default


def safe_save_json(filepath: str, data: dict) -> bool:
    """
    Safely save data to a JSON file.
    
    Args:
        filepath: Path to JSON file
        data: Dictionary to save
    
    Returns:
        True if successful, False otherwise
    """
    import json
    
    if not isinstance(data, dict):
        logger.error(f"Cannot save non-dict data to JSON: {type(data)}")
        return False
    
    try:
        # Write to temp file first, then rename (atomic on most systems)
        temp_path = filepath + ".tmp"
        
        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        # Replace original file
        if os.path.exists(filepath):
            os.replace(temp_path, filepath)
        else:
            os.rename(temp_path, filepath)
        
        logger.debug(f"Saved JSON to {filepath}")
        return True
        
    except (IOError, OSError, TypeError) as e:
        logger.error(f"Could not save to {filepath}: {e}")
        # Clean up temp file if it exists
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass
        return False


# =============================================================================
# MISCELLANEOUS UTILITIES
# =============================================================================

def clamp(value, min_val, max_val):
    """Clamp a value to a range."""
    return max(min_val, min(max_val, value))


def safe_int(value, default: int = 0) -> int:
    """Safely convert a value to int."""
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def safe_float(value, default: float = 0.0) -> float:
    """Safely convert a value to float."""
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def get_process_name() -> str:
    """Get the name of the current process."""
    if sys.platform == 'win32':
        return os.path.basename(sys.executable)
    return sys.argv[0] if sys.argv else "python"
