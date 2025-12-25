import os
import sys
from ctypes import windll

# --- AUDIO CONTROL SETUP ---
AUDIO_CONTROL_AVAILABLE = False
try:
    import comtypes

    # Try standard import (newer pycaw)
    try:
        from pycaw.utils import AudioUtilities
        from pycaw.interfaces import IAudioEndpointVolume
    except ImportError:
        # Fallback for older versions
        try:
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        except ImportError:
            pass

    AUDIO_CONTROL_AVAILABLE = True
except ImportError:
    print("[DEBUG] Warning: 'pycaw' or 'comtypes' not installed. Audio ducking disabled.")


class SingleInstanceChecker:
    def __init__(self, app_name):
        self.mutex_name = f"Global\\{app_name}_Mutex_v1.5_BROWSER"
        self.mutex = None
        self.last_error = 0

    def check(self):
        try:
            self.mutex = windll.kernel32.CreateMutexW(None, False, self.mutex_name)
            self.last_error = windll.kernel32.GetLastError()
        except Exception:
            pass

    def is_already_running(self):
        # ERROR_ALREADY_EXISTS = 183
        return self.last_error == 183

    def focus_existing_window(self, window_title):
        SW_RESTORE = 9
        try:
            hwnd = windll.user32.FindWindowW(None, window_title)
            if hwnd:
                windll.user32.ShowWindow(hwnd, SW_RESTORE)
                windll.user32.SetForegroundWindow(hwnd)
                return True
        except Exception:
            pass
        return False


class SystemAudioDucker:
    def __init__(self):
        self.original_volumes = {}
        self.is_ducked = False

    def duck(self, strength_percent=100):
        """
        Lowers the volume of ALL other applications.
        strength_percent: 0 = no change, 100 = silent.
        """
        if not AUDIO_CONTROL_AVAILABLE or self.is_ducked:
            return
        if strength_percent <= 0:
            return

        # 1. Initialize COM (Required for threading)
        try:
            comtypes.CoInitialize()
        except:
            pass

        print(f"[DEBUG] Ducking Audio: Target reduction {strength_percent}%")

        factor = 1.0 - (strength_percent / 100.0)
        factor = max(0.0, min(1.0, factor))

        current_pid = os.getpid()

        try:
            sessions = AudioUtilities.GetAllSessions()
            for session in sessions:
                try:
                    volume = session.SimpleAudioVolume
                    if not volume: continue

                    pid = 0
                    name = "System Sounds"

                    if session.Process:
                        pid = session.ProcessId
                        try:
                            name = session.Process.name()
                        except:
                            name = f"PID {pid}"

                    # 2. Logic: Duck EVERYTHING that is not this specific app
                    if pid != current_pid:
                        # Save original volume
                        current_vol = volume.GetMasterVolume()
                        self.original_volumes[session] = current_vol  # Use session obj as key for accuracy

                        # Set new volume
                        target_vol = current_vol * factor
                        volume.SetMasterVolume(target_vol, None)
                        # print(f"[DEBUG] Ducked {name}: {current_vol:.2f} -> {target_vol:.2f}")

                except Exception as e:
                    print(f"[DEBUG] Failed to duck session: {e}")
                    continue

            self.is_ducked = True

        except Exception as e:
            print(f"[DEBUG] Audio ducking CRITICAL error: {e}")

    def unduck(self):
        """Restores volume to original levels."""
        if not AUDIO_CONTROL_AVAILABLE or not self.is_ducked:
            return

        # 1. Initialize COM (Required for threading)
        try:
            comtypes.CoInitialize()
        except:
            pass

        print("[DEBUG] Restoring Audio Levels...")

        try:
            # We iterate through the sessions we saved
            for session, original_vol in self.original_volumes.items():
                try:
                    volume = session.SimpleAudioVolume
                    if volume:
                        volume.SetMasterVolume(original_vol, None)
                except:
                    # Session might have closed, ignore it
                    continue

            self.original_volumes.clear()
            self.is_ducked = False

        except Exception as e:
            print(f"[DEBUG] Audio unduck error: {e}")