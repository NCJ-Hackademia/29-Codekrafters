# agent_cmds.py — Jarvis core: model -> command -> execute -> confirm
import os, json, re, time, subprocess, webbrowser
from pathlib import Path
import requests
from colorama import init, Fore, Style
import mss, pyautogui, random
import psutil
import win32gui
import win32con
import win32process
import win32api
import speech_recognition as sr
import pyttsx3
import threading
import queue

init(autoreset=True)

# Config
MODEL = os.getenv("OLLAMA_MODEL", "chat_gemma1b_think")
API = os.getenv("OLLAMA_URL", "http://localhost:11434/api/chat")
ROOT = Path.cwd()
SCREEN_DIR = ROOT / "screenshots"; SCREEN_DIR.mkdir(exist_ok=True)
LOG_DIR = ROOT / "logs"; LOG_DIR.mkdir(exist_ok=True)

# Safety
SAFE_KEYS = {"space","enter","tab","up","down","left","right","esc","ctrl","alt","shift","f1","f2","f3","f4","f5","f6","f7","f8","f9","f10","f11","f12"}
MAX_PRESS_COUNT = 20
MIN_PRESS_DELAY = 0.02
SAFE_CMDS = {"whoami","ipconfig","dir","tasklist","echo","start","explorer"}  # whitelist for windows shell

# autorun toggle
AUTO_RUN = True

# Voice settings
VOICE_ACTIVATION = True
VOICE_ACTIVATION_PHRASE = "hey jarvis"
VOICE_ENGINE = None
VOICE_RECOGNIZER = None
VOICE_INPUT_QUEUE = queue.Queue()
VOICE_LISTENING = False

# Initialize voice engine
def init_voice():
    global VOICE_ENGINE
    try:
        VOICE_ENGINE = pyttsx3.init()
        voices = VOICE_ENGINE.getProperty('voices')
        
        # Find a female voice
        female_voice = None
        for voice in voices:
            if 'female' in voice.name.lower() or 'zira' in voice.name.lower() or 'hazel' in voice.name.lower():
                female_voice = voice
                break
        
        if female_voice:
            VOICE_ENGINE.setProperty('voice', female_voice.id)
        else:
            # If no female voice found, use the first available
            if voices:
                VOICE_ENGINE.setProperty('voice', voices[0].id)
        
        # Set voice properties for better quality
        VOICE_ENGINE.setProperty('rate', 180)  # Speed of speech
        VOICE_ENGINE.setProperty('volume', 0.9)  # Volume (0.0 to 1.0)
        
        # Start the speech worker
        start_speech_worker()
        
        print(Fore.GREEN + "✅ Voice engine initialized successfully!" + Style.RESET_ALL)
        return True
    except Exception as e:
        print(Fore.RED + f"❌ Failed to initialize voice engine: {e}" + Style.RESET_ALL)
        return False

# Initialize speech recognition
def init_speech_recognition():
    global VOICE_RECOGNIZER
    try:
        VOICE_RECOGNIZER = sr.Recognizer()
        VOICE_RECOGNIZER.energy_threshold = 4000
        VOICE_RECOGNIZER.dynamic_energy_threshold = True
        VOICE_RECOGNIZER.pause_threshold = 0.8
        print(Fore.GREEN + "✅ Speech recognition initialized successfully!" + Style.RESET_ALL)
        return True
    except Exception as e:
        print(Fore.RED + f"❌ Failed to initialize speech recognition: {e}" + Style.RESET_ALL)
        return False

# Speech queue system to prevent threading conflicts
SPEECH_QUEUE = queue.Queue()
SPEECH_THREAD = None
SPEECH_RUNNING = False

def speech_worker():
    """Background worker for speech synthesis"""
    global SPEECH_RUNNING
    SPEECH_RUNNING = True
    
    while SPEECH_RUNNING:
        try:
            text = SPEECH_QUEUE.get(timeout=1)
            if text == "STOP":
                break
            try:
                VOICE_ENGINE.say(text)
                VOICE_ENGINE.runAndWait()
            except Exception as e:
                print(Fore.RED + f"❌ Speech error: {e}" + Style.RESET_ALL)
        except queue.Empty:
            continue
        except Exception as e:
            print(Fore.RED + f"❌ Speech worker error: {e}" + Style.RESET_ALL)

def start_speech_worker():
    """Start the speech worker thread"""
    global SPEECH_THREAD
    if not SPEECH_THREAD or not SPEECH_THREAD.is_alive():
        SPEECH_THREAD = threading.Thread(target=speech_worker)
        SPEECH_THREAD.daemon = True
        SPEECH_THREAD.start()
        print(Fore.GREEN + "✅ Speech worker started" + Style.RESET_ALL)

def stop_speech_worker():
    """Stop the speech worker thread"""
    global SPEECH_RUNNING
    SPEECH_RUNNING = False
    if SPEECH_QUEUE:
        SPEECH_QUEUE.put("STOP")

# Speak text with female voice
def speak_text(text):
    if VOICE_ENGINE and SPEECH_QUEUE:
        try:
            SPEECH_QUEUE.put(text)
            return True
        except Exception as e:
            print(Fore.RED + f"❌ Speech error: {e}" + Style.RESET_ALL)
            return False
    return False

# Listen for voice input
def listen_for_voice():
    global VOICE_RECOGNIZER
    if not VOICE_RECOGNIZER:
        return None
    
    try:
        with sr.Microphone() as source:
            print(Fore.YELLOW + "🎤 Listening for voice input..." + Style.RESET_ALL)
            VOICE_RECOGNIZER.adjust_for_ambient_noise(source, duration=0.5)
            audio = VOICE_RECOGNIZER.listen(source, timeout=5, phrase_time_limit=10)
            
            print(Fore.YELLOW + "🔄 Processing speech..." + Style.RESET_ALL)
            text = VOICE_RECOGNIZER.recognize_google(audio)
            print(Fore.GREEN + f"🎯 Voice input: {text}" + Style.RESET_ALL)
            return text.lower()
    except sr.WaitTimeoutError:
        print(Fore.YELLOW + "⏰ No voice input detected (timeout)" + Style.RESET_ALL)
        return None
    except sr.UnknownValueError:
        print(Fore.YELLOW + "❓ Could not understand voice input" + Style.RESET_ALL)
        return None
    except sr.RequestError as e:
        print(Fore.RED + f"❌ Speech recognition service error: {e}" + Style.RESET_ALL)
        return None
    except Exception as e:
        print(Fore.RED + f"❌ Voice listening error: {e}" + Style.RESET_ALL)
        return None

# Voice activation listener
def voice_activation_listener():
    global VOICE_LISTENING, VOICE_ACTIVATION
    
    print(Fore.GREEN + f"🎤 Voice activation listener started! Say '{VOICE_ACTIVATION_PHRASE}' to activate." + Style.RESET_ALL)
    
    while VOICE_ACTIVATION:
        try:
            if not VOICE_LISTENING:
                print(Fore.YELLOW + "🎤 Listening for activation phrase..." + Style.RESET_ALL)
                text = listen_for_voice()
                if text and VOICE_ACTIVATION_PHRASE in text:
                    print(Fore.GREEN + f"🎯 Voice activation detected: '{text}'" + Style.RESET_ALL)
                    
                    # Check if the command is included in the same sentence
                    # Remove the activation phrase to get the actual command
                    command_part = text.replace(VOICE_ACTIVATION_PHRASE, "").strip()
                    
                    if command_part and len(command_part) > 3:  # If there's a meaningful command
                        print(Fore.GREEN + f"🎯 Command extracted from activation: {command_part}" + Style.RESET_ALL)
                        speak_text("Got it! Working on it.")
                        VOICE_INPUT_QUEUE.put(command_part)
                        VOICE_LISTENING = True
                        time.sleep(1)
                    else:
                        # No command in the activation phrase, ask for one
                        speak_text("Hello! I'm listening. What can I help you with?")
                        time.sleep(2)
                        
                        # Get the actual command
                        print(Fore.YELLOW + "🎤 Listening for command..." + Style.RESET_ALL)
                        command_text = listen_for_voice()
                        if command_text:
                            print(Fore.GREEN + f"🎯 Command received: {command_text}" + Style.RESET_ALL)
                            VOICE_INPUT_QUEUE.put(command_text)
                            VOICE_LISTENING = True
                            time.sleep(2)
                        else:
                            print(Fore.YELLOW + "No command received, continuing to listen..." + Style.RESET_ALL)
                else:
                    if text:
                        print(Fore.YELLOW + f"Heard: '{text}' (no activation phrase)" + Style.RESET_ALL)
                    time.sleep(0.5)  # Short delay between checks
            else:
                time.sleep(0.1)
        except Exception as e:
            print(Fore.RED + f"❌ Voice activation error: {e}" + Style.RESET_ALL)
            time.sleep(1)

# Start voice activation
def start_voice_activation():
    global VOICE_ACTIVATION
    if VOICE_ACTIVATION and VOICE_ENGINE and VOICE_RECOGNIZER:
        print(Fore.GREEN + f"🎤 Voice activation started! Say '{VOICE_ACTIVATION_PHRASE}' to activate." + Style.RESET_ALL)
        speak_text(f"Voice activation enabled. Say {VOICE_ACTIVATION_PHRASE} to activate me.")
        
        voice_thread = threading.Thread(target=voice_activation_listener)
        voice_thread.daemon = True
        voice_thread.start()
        return True
    return False

# Stop voice activation
def stop_voice_activation():
    global VOICE_ACTIVATION
    VOICE_ACTIVATION = False
    print(Fore.YELLOW + "🎤 Voice activation stopped." + Style.RESET_ALL)
    speak_text("Voice activation disabled.")

# --- Enhanced desktop automation tools ---

def open_chrome_tool(args=None):
    """Open Google Chrome browser"""
    try:
        # Try multiple Chrome paths
        chrome_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            r"C:\Users\{}\AppData\Local\Google\Chrome\Application\chrome.exe".format(os.getenv('USERNAME')),
        ]
        
        for path in chrome_paths:
            if os.path.exists(path):
                subprocess.Popen([path])
                return {"ok": True, "action": "opened_chrome", "path": path}
        
        # Fallback: try to start chrome from PATH
        subprocess.Popen(["chrome"])
        return {"ok": True, "action": "opened_chrome", "method": "path"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def switch_tab_tool(args=None):
    """Switch to next tab (Ctrl+Tab)"""
    try:
        pyautogui.hotkey('ctrl', 'tab')
        time.sleep(0.05)
        return {"ok": True, "action": "switched_tab_next"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def switch_tab_back_tool(args=None):
    """Switch to previous tab (Ctrl+Shift+Tab)"""
    try:
        pyautogui.hotkey('ctrl', 'shift', 'tab')
        time.sleep(0.05)
        return {"ok": True, "action": "switched_tab_prev"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def switch_app_tool(args=None):
    """Switch between applications (Alt+Tab)"""
    try:
        pyautogui.hotkey('alt', 'tab')
        time.sleep(0.1)
        return {"ok": True, "action": "switched_app"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def close_tab_tool(args=None):
    """Close current tab (Ctrl+W)"""
    try:
        pyautogui.hotkey('ctrl', 'w')
        time.sleep(0.05)
        return {"ok": True, "action": "closed_tab"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def new_tab_tool(args=None):
    """Open new tab (Ctrl+T)"""
    try:
        pyautogui.hotkey('ctrl', 't')
        time.sleep(0.05)
        return {"ok": True, "action": "opened_new_tab"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def refresh_page_tool(args=None):
    """Refresh current page (F5)"""
    try:
        pyautogui.press('f5')
        time.sleep(0.05)
        return {"ok": True, "action": "refreshed_page"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def go_back_tool(args=None):
    """Go back in browser (Alt+Left)"""
    try:
        pyautogui.hotkey('alt', 'left')
        time.sleep(0.05)
        return {"ok": True, "action": "went_back"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def go_forward_tool(args=None):
    """Go forward in browser (Alt+Right)"""
    try:
        pyautogui.hotkey('alt', 'right')
        time.sleep(0.05)
        return {"ok": True, "action": "went_forward"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def minimize_window_tool(args=None):
    """Minimize current window"""
    try:
        pyautogui.hotkey('win', 'down')
        time.sleep(0.05)
        return {"ok": True, "action": "minimized_window"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def maximize_window_tool(args=None):
    """Maximize current window"""
    try:
        pyautogui.hotkey('win', 'up')
        time.sleep(0.05)
        return {"ok": True, "action": "maximized_window"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def close_window_tool(args=None):
    """Close current window (Alt+F4)"""
    try:
        pyautogui.hotkey('alt', 'f4')
        time.sleep(0.05)
        return {"ok": True, "action": "closed_window"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def open_explorer_tool(args=None):
    """Open File Explorer"""
    try:
        subprocess.Popen(["explorer"])
        return {"ok": True, "action": "opened_explorer"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def open_notepad_tool(args=None):
    """Open Notepad"""
    try:
        subprocess.Popen(["notepad"])
        return {"ok": True, "action": "opened_notepad"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def open_calculator_tool(args=None):
    """Open Calculator"""
    try:
        subprocess.Popen(["calc"])
        return {"ok": True, "action": "opened_calculator"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def open_camera_tool(args=None):
    """Open Windows Camera app"""
    try:
        # Try multiple camera app paths
        camera_paths = [
            "ms-camera:",
            "ms-camera://",
            "start ms-camera:",
            "start ms-camera://"
        ]
        
        # Method 1: Try direct camera app launch
        try:
            subprocess.Popen(["start", "ms-camera:"], shell=True)
            return {"ok": True, "action": "opened_camera", "method": "ms-camera"}
        except:
            pass
        
        # Method 2: Try Windows Camera executable
        try:
            subprocess.Popen(["WindowsCamera.exe"])
            return {"ok": True, "action": "opened_camera", "method": "executable"}
        except:
            pass
        
        # Method 3: Try through shell
        try:
            subprocess.run(["cmd", "/c", "start", "ms-camera:"], shell=True)
            return {"ok": True, "action": "opened_camera", "method": "shell"}
        except:
            pass
        
        # Method 4: Try through PowerShell
        try:
            subprocess.run(["powershell", "-Command", "Start-Process", "ms-camera:"], shell=True)
            return {"ok": True, "action": "opened_camera", "method": "powershell"}
        except:
            pass
        
        return {"ok": False, "error": "Could not open camera app"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def open_any_app_tool(args=None):
    """Open any application by name or path"""
    args = args or {}
    app_name = args.get("app", "").strip()
    
    if not app_name:
        return {"ok": False, "error": "No app name provided"}
    
    try:
        # Try multiple methods to open the app
        
        # Method 1: Direct subprocess
        try:
            subprocess.Popen([app_name])
            return {"ok": True, "action": "opened_app", "app": app_name, "method": "direct"}
        except:
            pass
        
        # Method 2: With shell
        try:
            subprocess.Popen([app_name], shell=True)
            return {"ok": True, "action": "opened_app", "app": app_name, "method": "shell"}
        except:
            pass
        
        # Method 3: Using start command
        try:
            subprocess.run(["start", app_name], shell=True)
            return {"ok": True, "action": "opened_app", "app": app_name, "method": "start"}
        except:
            pass
        
        # Method 4: Using explorer
        try:
            subprocess.run(["explorer", app_name], shell=True)
            return {"ok": True, "action": "opened_app", "app": app_name, "method": "explorer"}
        except:
            pass
        
        # Method 5: Try to find in common paths
        common_paths = [
            r"C:\Program Files",
            r"C:\Program Files (x86)",
            r"C:\Users\{}\AppData\Local".format(os.getenv('USERNAME')),
            r"C:\Users\{}\AppData\Roaming".format(os.getenv('USERNAME'))
        ]
        
        for base_path in common_paths:
            if os.path.exists(base_path):
                for root, dirs, files in os.walk(base_path):
                    for file in files:
                        if app_name.lower() in file.lower() and file.endswith('.exe'):
                            full_path = os.path.join(root, file)
                            try:
                                subprocess.Popen([full_path])
                                return {"ok": True, "action": "opened_app", "app": app_name, "path": full_path, "method": "search"}
                            except:
                                continue
        
        return {"ok": False, "error": f"Could not open app: {app_name}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def copy_tool(args=None):
    """Copy selection (Ctrl+C)"""
    try:
        pyautogui.hotkey('ctrl', 'c')
        time.sleep(0.05)
        return {"ok": True, "action": "copied"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def paste_tool(args=None):
    """Paste (Ctrl+V)"""
    try:
        pyautogui.hotkey('ctrl', 'v')
        time.sleep(0.05)
        return {"ok": True, "action": "pasted"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def cut_tool(args=None):
    """Cut selection (Ctrl+X)"""
    try:
        pyautogui.hotkey('ctrl', 'x')
        time.sleep(0.05)
        return {"ok": True, "action": "cut"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def undo_tool(args=None):
    """Undo (Ctrl+Z)"""
    try:
        pyautogui.hotkey('ctrl', 'z')
        time.sleep(0.05)
        return {"ok": True, "action": "undone"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def redo_tool(args=None):
    """Redo (Ctrl+Y)"""
    try:
        pyautogui.hotkey('ctrl', 'y')
        time.sleep(0.05)
        return {"ok": True, "action": "redone"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def select_all_tool(args=None):
    """Select all (Ctrl+A)"""
    try:
        pyautogui.hotkey('ctrl', 'a')
        time.sleep(0.05)
        return {"ok": True, "action": "selected_all"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def save_tool(args=None):
    """Save (Ctrl+S)"""
    try:
        pyautogui.hotkey('ctrl', 's')
        time.sleep(0.05)
        return {"ok": True, "action": "saved"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def open_file_tool(args=None):
    """Open file dialog (Ctrl+O)"""
    try:
        pyautogui.hotkey('ctrl', 'o')
        time.sleep(0.05)
        return {"ok": True, "action": "opened_file_dialog"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def print_tool(args=None):
    """Print dialog (Ctrl+P)"""
    try:
        pyautogui.hotkey('ctrl', 'p')
        time.sleep(0.05)
        return {"ok": True, "action": "opened_print_dialog"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def find_tool(args=None):
    """Find dialog (Ctrl+F)"""
    try:
        pyautogui.hotkey('ctrl', 'f')
        time.sleep(0.05)
        return {"ok": True, "action": "opened_find_dialog"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def replace_tool(args=None):
    """Replace dialog (Ctrl+H)"""
    try:
        pyautogui.hotkey('ctrl', 'h')
        time.sleep(0.05)
        return {"ok": True, "action": "opened_replace_dialog"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def zoom_in_tool(args=None):
    """Zoom in (Ctrl+Plus)"""
    try:
        pyautogui.hotkey('ctrl', '+')
        time.sleep(0.05)
        return {"ok": True, "action": "zoomed_in"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def zoom_out_tool(args=None):
    """Zoom out (Ctrl+Minus)"""
    try:
        pyautogui.hotkey('ctrl', '-')
        time.sleep(0.05)
        return {"ok": True, "action": "zoomed_out"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def zoom_reset_tool(args=None):
    """Reset zoom (Ctrl+0)"""
    try:
        pyautogui.hotkey('ctrl', '0')
        time.sleep(0.05)
        return {"ok": True, "action": "reset_zoom"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def lock_screen_tool(args=None):
    """Lock the screen (Win+L)"""
    try:
        pyautogui.hotkey('win', 'l')
        time.sleep(0.05)
        return {"ok": True, "action": "locked_screen"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def show_desktop_tool(args=None):
    """Show desktop (Win+D)"""
    try:
        pyautogui.hotkey('win', 'd')
        time.sleep(0.05)
        return {"ok": True, "action": "showed_desktop"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def task_manager_tool(args=None):
    """Open Task Manager (Ctrl+Shift+Esc)"""
    try:
        pyautogui.hotkey('ctrl', 'shift', 'esc')
        time.sleep(0.05)
        return {"ok": True, "action": "opened_task_manager"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def run_dialog_tool(args=None):
    """Open Run dialog (Win+R)"""
    try:
        pyautogui.hotkey('win', 'r')
        time.sleep(0.05)
        return {"ok": True, "action": "opened_run_dialog"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def settings_tool(args=None):
    """Open Windows Settings (Win+I)"""
    try:
        pyautogui.hotkey('win', 'i')
        time.sleep(0.05)
        return {"ok": True, "action": "opened_settings"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def action_center_tool(args=None):
    """Open Action Center (Win+A)"""
    try:
        pyautogui.hotkey('win', 'a')
        time.sleep(0.05)
        return {"ok": True, "action": "opened_action_center"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def search_tool(args=None):
    """Open Windows Search (Win+S)"""
    try:
        pyautogui.hotkey('win', 's')
        time.sleep(0.05)
        return {"ok": True, "action": "opened_search"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def volume_up_tool(args=None):
    """Increase volume using Windows API"""
    try:
        # Use Windows API to increase volume
        import ctypes
        from ctypes import cast, POINTER
        from comtypes import CLSCTX_ALL
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        
        # Get current volume
        current_volume = volume.GetMasterVolumeLevelScalar()
        # Increase by 10%
        new_volume = min(1.0, current_volume + 0.1)
        volume.SetMasterVolumeLevelScalar(new_volume, None)
        
        return {"ok": True, "action": "volume_increased", "from": f"{current_volume:.1%}", "to": f"{new_volume:.1%}"}
    except ImportError:
        # Fallback to keyboard if pycaw not available
        try:
            pyautogui.press('volumeup')
            time.sleep(0.05)
            return {"ok": True, "action": "volume_increased", "method": "keyboard"}
        except Exception as e:
            return {"ok": False, "error": str(e)}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def volume_down_tool(args=None):
    """Decrease volume using Windows API"""
    try:
        # Use Windows API to decrease volume
        import ctypes
        from ctypes import cast, POINTER
        from comtypes import CLSCTX_ALL
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        
        # Get current volume
        current_volume = volume.GetMasterVolumeLevelScalar()
        # Decrease by 10%
        new_volume = max(0.0, current_volume - 0.1)
        volume.SetMasterVolumeLevelScalar(new_volume, None)
        
        return {"ok": True, "action": "volume_decreased", "from": f"{current_volume:.1%}", "to": f"{new_volume:.1%}"}
    except ImportError:
        # Fallback to keyboard if pycaw not available
        try:
            pyautogui.press('volumedown')
            time.sleep(0.05)
            return {"ok": True, "action": "volume_decreased", "method": "keyboard"}
        except Exception as e:
            return {"ok": False, "error": str(e)}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def mute_tool(args=None):
    """Mute/unmute volume using Windows API"""
    try:
        # Use Windows API to toggle mute
        import ctypes
        from ctypes import cast, POINTER
        from comtypes import CLSCTX_ALL
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        
        # Get current mute state
        current_mute = volume.GetMute()
        # Toggle mute
        new_mute = not current_mute
        volume.SetMute(new_mute, None)
        
        status = "muted" if new_mute else "unmuted"
        return {"ok": True, "action": f"volume_{status}", "mute_state": new_mute}
    except ImportError:
        # Fallback to keyboard if pycaw not available
        try:
            pyautogui.press('volumemute')
            time.sleep(0.05)
            return {"ok": True, "action": "volume_toggled", "method": "keyboard"}
        except Exception as e:
            return {"ok": False, "error": str(e)}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def play_pause_tool(args=None):
    """Play/pause media using Windows media keys"""
    try:
        # Try multiple methods for media control
        try:
            # Method 1: Direct media key
            pyautogui.press('playpause')
            time.sleep(0.05)
            return {"ok": True, "action": "media_play_pause", "method": "media_key"}
        except:
            # Method 2: Windows media control
            pyautogui.hotkey('ctrl', 'shift', 'p')
            time.sleep(0.05)
            return {"ok": True, "action": "media_play_pause", "method": "hotkey"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def next_track_tool(args=None):
    """Next media track using Windows media keys"""
    try:
        # Try multiple methods for media control
        try:
            # Method 1: Direct media key
            pyautogui.press('nexttrack')
            time.sleep(0.05)
            return {"ok": True, "action": "next_track", "method": "media_key"}
        except:
            # Method 2: Windows media control
            pyautogui.hotkey('ctrl', 'shift', 'right')
            time.sleep(0.05)
            return {"ok": True, "action": "next_track", "method": "hotkey"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def prev_track_tool(args=None):
    """Previous media track using Windows media keys"""
    try:
        # Try multiple methods for media control
        try:
            # Method 1: Direct media key
            pyautogui.press('prevtrack')
            time.sleep(0.05)
            return {"ok": True, "action": "previous_track", "method": "media_key"}
        except:
            # Method 2: Windows media control
            pyautogui.hotkey('ctrl', 'shift', 'left')
            time.sleep(0.05)
            return {"ok": True, "action": "previous_track", "method": "hotkey"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def brightness_up_tool(args=None):
    """Increase brightness"""
    try:
        pyautogui.press('brightnessup')
        time.sleep(0.05)
        return {"ok": True, "action": "brightness_increased"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def brightness_down_tool(args=None):
    """Decrease brightness"""
    try:
        pyautogui.press('brightnessdown')
        time.sleep(0.05)
        return {"ok": True, "action": "brightness_decreased"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

# ---------- Original tools ----------
def take_screenshot_tool(args=None):
    ts = time.strftime("%Y%m%d_%H%M%S")
    path = str(SCREEN_DIR / f"screenshot_{ts}.png")
    try:
        with mss.mss() as sct:
            sct.shot(output=path)
        return {"ok": True, "path": path}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def press_key_tool(args=None):
    args = args or {}
    key = str(args.get("key","")).strip().lower()
    count = int(args.get("count",1))
    delay = float(args.get("delay",0.05))
    if key in ("spacebar","space bar"): key = "space"
    if key not in SAFE_KEYS:
        return {"ok": False, "error": f"key '{key}' not allowed"}
    if count < 1 or count > MAX_PRESS_COUNT:
        return {"ok": False, "error": f"count out of range 1..{MAX_PRESS_COUNT}"}
    if delay < MIN_PRESS_DELAY: delay = MIN_PRESS_DELAY
    try:
        for _ in range(count):
            pyautogui.press(key)
            time.sleep(delay)
        return {"ok": True, "pressed": key, "count": count}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def welcome_home_tool(args=None):
    weather = {"temp_c": random.randint(18,34), "condition": random.choice(["sunny","cloudy","light rain","clear"])}
    notifications = random.sample([
        "Team sync at 6pm",
        "New email from Alex",
        "Package delivered",
        "Reminder: electrician tomorrow",
        "Fitness: 3500 steps today"
    ], k=random.randint(0,3))
    return {"ok": True, "weather": weather, "notifications": notifications}

def open_path_tool(args=None):
    args = args or {}
    path = args.get("path","")
    if not path: return {"ok": False, "error": "no path"}
    try:
        if path.startswith("http://") or path.startswith("https://"):
            webbrowser.open(path)
        else:
            os.startfile(path)
        return {"ok": True, "path": os.path.abspath(path)}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def run_cmd_tool(args=None):
    args = args or {}
    cmd = args.get("cmd","")
    if not cmd: return {"ok": False, "error": "no cmd"}
    base = cmd.split()[0].lower()
    if base not in SAFE_CMDS:
        return {"ok": False, "error": f"cmd '{base}' not allowed"}
    try:
        out = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT, text=True, timeout=10)
        return {"ok": True, "output": out.strip()}
    except Exception as e:
        return {"ok": False, "error": str(e)}

# Enhanced tool registry with all new tools
TOOL_REGISTRY = {
    # Browser & Tab Management
    "open_chrome": open_chrome_tool,
    "switch_tab": switch_tab_tool,
    "switch_tab_back": switch_tab_back_tool,
    "close_tab": close_tab_tool,
    "new_tab": new_tab_tool,
    "refresh_page": refresh_page_tool,
    "go_back": go_back_tool,
    "go_forward": go_forward_tool,
    
    # App Management
    "switch_app": switch_app_tool,
    "minimize_window": minimize_window_tool,
    "maximize_window": maximize_window_tool,
    "close_window": close_window_tool,
    
    # System Apps
    "open_explorer": open_explorer_tool,
    "open_notepad": open_notepad_tool,
    "open_calculator": open_calculator_tool,
    "open_camera": open_camera_tool,
    "open_any_app": open_any_app_tool,
    
    # File Operations
    "copy": copy_tool,
    "paste": paste_tool,
    "cut": cut_tool,
    "undo": undo_tool,
    "redo": redo_tool,
    "select_all": select_all_tool,
    "save": save_tool,
    "open_file": open_file_tool,
    "print": print_tool,
    "find": find_tool,
    "replace": replace_tool,
    
    # View Controls
    "zoom_in": zoom_in_tool,
    "zoom_out": zoom_out_tool,
    "zoom_reset": zoom_reset_tool,
    
    # System Controls
    "lock_screen": lock_screen_tool,
    "show_desktop": show_desktop_tool,
    "task_manager": task_manager_tool,
    "run_dialog": run_dialog_tool,
    "settings": settings_tool,
    "action_center": action_center_tool,
    "search": search_tool,
    
    # Media Controls
    "volume_up": volume_up_tool,
    "volume_down": volume_down_tool,
    "mute": mute_tool,
    "play_pause": play_pause_tool,
    "next_track": next_track_tool,
    "prev_track": prev_track_tool,
    
    # Display Controls
    "brightness_up": brightness_up_tool,
    "brightness_down": brightness_down_tool,
    
    # Original tools
    "take_screenshot": take_screenshot_tool,
    "press_key": press_key_tool,
    "welcome_home": welcome_home_tool,
    "open_path": open_path_tool,
    "run_cmd": run_cmd_tool
}

# logging
def log_tool_call(user, cmd, result):
    entry = {"ts": time.time(), "user": user, "cmd": cmd, "result": result}
    with open(LOG_DIR / "tool_calls.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

# helpers
CMD_RE = re.compile(r"<<COMMAND>>(.*?)<<END_COMMAND>>", re.S | re.I)

def call_model(messages, stream=False):
    payload = {"model": MODEL, "messages": messages, "stream": False}
    r = requests.post(API, json=payload, timeout=60)
    r.raise_for_status()
    j = r.json()
    return j.get("message", {}).get("content",""), j

def extract_commands(text):
    text_norm = text
    matches = CMD_RE.findall(text_norm)
    cmds = []
    for m in matches:
        try:
            cmd = json.loads(m.strip())
            if isinstance(cmd, dict): cmds.append(cmd)
        except Exception:
            continue
    return cmds

def detect_fallback(text):
    low = text.lower()
    # Screenshot commands
    if any(kw in low for kw in ["screenshot","take a screenshot","capture the screen","capture screenshot"]):
        return {"name":"take_screenshot","args":{}}
    
    # Chrome and browser commands
    if any(kw in low for kw in ["open chrome","launch chrome","start chrome","chrome browser"]):
        return {"name":"open_chrome","args":{}}
    if any(kw in low for kw in ["switch tab","next tab","change tab"]):
        return {"name":"switch_tab","args":{}}
    if any(kw in low for kw in ["previous tab","back tab","last tab"]):
        return {"name":"switch_tab_back","args":{}}
    if any(kw in low for kw in ["new tab","open tab"]):
        return {"name":"new_tab","args":{}}
    if any(kw in low for kw in ["close tab","shut tab"]):
        return {"name":"close_tab","args":{}}
    if any(kw in low for kw in ["refresh","reload","f5"]):
        return {"name":"refresh_page","args":{}}
    if any(kw in low for kw in ["go back","back","browser back"]):
        return {"name":"go_back","args":{}}
    if any(kw in low for kw in ["go forward","forward","browser forward"]):
        return {"name":"go_forward","args":{}}
    
    # App switching
    if any(kw in low for kw in ["switch app","switch application","alt tab","change app"]):
        return {"name":"switch_app","args":{}}
    
    # Window management
    if any(kw in low for kw in ["minimize","minimize window","small window"]):
        return {"name":"minimize_window","args":{}}
    if any(kw in low for kw in ["maximize","maximize window","full screen"]):
        return {"name":"maximize_window","args":{}}
    if any(kw in low for kw in ["close window","shut window"]):
        return {"name":"close_window","args":{}}
    
    # System apps
    if any(kw in low for kw in ["open explorer","file explorer","explorer"]):
        return {"name":"open_explorer","args":{}}
    if any(kw in low for kw in ["open notepad","notepad","text editor"]):
        return {"name":"open_notepad","args":{}}
    if any(kw in low for kw in ["open calculator","calculator","calc"]):
        return {"name":"open_calculator","args":{}}
    if any(kw in low for kw in ["open camera","camera","take picture","take photo","take pic","webcam","picture","photo"]):
        return {"name":"open_camera","args":{}}
    if any(kw in low for kw in ["open app","launch app","start app","run app"]):
        # Extract app name from the command
        app_name = low.replace("open app", "").replace("launch app", "").replace("start app", "").replace("run app", "").strip()
        if app_name:
            return {"name":"open_any_app","args":{"app": app_name}}
    
    # File operations
    if any(kw in low for kw in ["copy","copy text","copy selection"]):
        return {"name":"copy","args":{}}
    if any(kw in low for kw in ["paste","paste text","paste from clipboard"]):
        return {"name":"paste","args":{}}
    if any(kw in low for kw in ["cut","cut text","cut selection"]):
        return {"name":"cut","args":{}}
    if any(kw in low for kw in ["undo","undo action","reverse"]):
        return {"name":"undo","args":{}}
    if any(kw in low for kw in ["redo","redo action","repeat"]):
        return {"name":"redo","args":{}}
    if any(kw in low for kw in ["select all","select everything","highlight all"]):
        return {"name":"select_all","args":{}}
    if any(kw in low for kw in ["save","save file","save document"]):
        return {"name":"save","args":{}}
    if any(kw in low for kw in ["open file","file open","browse files"]):
        return {"name":"open_file","args":{}}
    if any(kw in low for kw in ["print","print document","print dialog"]):
        return {"name":"print","args":{}}
    if any(kw in low for kw in ["find","find text","search text"]):
        return {"name":"find","args":{}}
    if any(kw in low for kw in ["replace","replace text","find and replace"]):
        return {"name":"replace","args":{}}
    
    # View controls
    if any(kw in low for kw in ["zoom in","zoom","enlarge","bigger"]):
        return {"name":"zoom_in","args":{}}
    if any(kw in low for kw in ["zoom out","zoom out","smaller","reduce"]):
        return {"name":"zoom_out","args":{}}
    if any(kw in low for kw in ["reset zoom","normal size","default zoom"]):
        return {"name":"zoom_reset","args":{}}
    
    # System controls
    if any(kw in low for kw in ["lock screen","lock computer","lock pc"]):
        return {"name":"lock_screen","args":{}}
    if any(kw in low for kw in ["show desktop","desktop","hide windows"]):
        return {"name":"show_desktop","args":{}}
    if any(kw in low for kw in ["task manager","processes","running apps"]):
        return {"name":"task_manager","args":{}}
    if any(kw in low for kw in ["run dialog","run command","win r"]):
        return {"name":"run_dialog","args":{}}
    if any(kw in low for kw in ["settings","windows settings","system settings"]):
        return {"name":"settings","args":{}}
    if any(kw in low for kw in ["action center","notifications","quick settings"]):
        return {"name":"action_center","args":{}}
    if any(kw in low for kw in ["search","windows search","find files"]):
        return {"name":"search","args":{}}
    
    # Media controls
    if any(kw in low for kw in ["volume up","increase volume","louder","turn up"]):
        return {"name":"volume_up","args":{}}
    if any(kw in low for kw in ["volume down","decrease volume","quieter","turn down"]):
        return {"name":"volume_down","args":{}}
    if any(kw in low for kw in ["mute","silence","no sound"]):
        return {"name":"mute","args":{}}
    if any(kw in low for kw in ["play pause","play","pause","media control"]):
        return {"name":"play_pause","args":{}}
    if any(kw in low for kw in ["next track","next song","next track"]):
        return {"name":"next_track","args":{}}
    if any(kw in low for kw in ["previous track","last song","previous track"]):
        return {"name":"prev_track","args":{}}
    
    # Display controls
    if any(kw in low for kw in ["brightness up","increase brightness","brighter","more light"]):
        return {"name":"brightness_up","args":{}}
    if any(kw in low for kw in ["brightness down","decrease brightness","dimmer","less light"]):
        return {"name":"brightness_down","args":{}}
    
    # Legacy fallbacks
    if "jump" in low or "press space" in low or "spacebar" in low:
        return {"name":"press_key","args":{"key":"space","count":1}}
    if "next" == low.strip() or low.strip().startswith("next"):
        return {"name":"press_key","args":{"key":"right","count":1}}
    if "previous" == low.strip() or "previous" in low:
        return {"name":"press_key","args":{"key":"left","count":1}}
    if "i am back" in low or "i'm back" in low:
        return {"name":"welcome_home","args":{}}
    
    return None

# main loop
def main():
    print(Fore.GREEN + f"Jarvis agent ready (model={MODEL}). Type /quit, /autorun on, /autorun off.\n")
    print(Fore.CYAN + "Available commands: open chrome, switch tab, copy, paste, take screenshot, etc.")
    print(Fore.CYAN + "Voice commands: /voice on, /voice off, /listen, /test_voice\n")
    print(Fore.CYAN + "Just type naturally and I'll understand what you want!\n")
    
    # Initialize voice capabilities
    voice_ready = init_voice() and init_speech_recognition()
    if voice_ready:
        print(Fore.GREEN + "🎤 Voice capabilities initialized successfully!" + Style.RESET_ALL)
        speak_text("Hello! I'm Jarvis, your voice-activated assistant. I'm ready to help you.")
        
        # Start voice activation automatically
        print(Fore.GREEN + "🎤 Starting voice activation automatically..." + Style.RESET_ALL)
        start_voice_activation()
    else:
        print(Fore.YELLOW + "⚠️ Voice capabilities not available. Running in text-only mode." + Style.RESET_ALL)
    
    system_msg = {"role":"system","content":"You are Jarvis, a helpful desktop assistant. When users ask you to perform actions, respond with the appropriate command in this exact format: <<COMMAND>>{\"name\":\"tool_name\",\"args\":{}}<<END_COMMAND>>. Available tools include: take_screenshot, open_chrome, switch_tab, copy, paste, open_notepad, open_calculator, etc. Always respond conversationally and include the command block."}
    messages = [system_msg]

    global AUTO_RUN, VOICE_ACTIVATION

    while True:
        user = None
        # Check for voice input from queue
        try:
            if not VOICE_INPUT_QUEUE.empty():
                user = VOICE_INPUT_QUEUE.get_nowait()
                print(Fore.GREEN + f"🎤 Voice input received: {user}" + Style.RESET_ALL)
                global VOICE_LISTENING
                VOICE_LISTENING = False
            else:
                # Only ask for text input if no voice input is available
                try:
                    # Use a timeout-based approach for Windows
                    import msvcrt
                    if msvcrt.kbhit():
                        user = input(Fore.CYAN + "You: " + Style.RESET_ALL).strip()
                    else:
                        # No keyboard input, continue to check voice queue again
                        time.sleep(0.1)
                        continue
                except ImportError:
                    # Fallback for non-Windows systems
                    try:
                        user = input(Fore.CYAN + "You: " + Style.RESET_ALL).strip()
                    except (KeyboardInterrupt, EOFError):
                        print("\nBye!"); break
        except (KeyboardInterrupt, EOFError):
            print("\nBye!"); break
        if not user: continue
        if user.lower() in ("/quit","/exit"):
            print("Bye!"); break
        if user.lower().startswith("/autorun"):
            opt = user.split()[-1].lower() if len(user.split())>1 else ""
            if opt == "off":
                AUTO_RUN = False
                print(Fore.YELLOW + "AUTO_RUN disabled. You will need to confirm tool runs.")
                speak_text("Auto run disabled. You will need to confirm tool runs.")
            elif opt == "on":
                AUTO_RUN = True
                print(Fore.YELLOW + "AUTO_RUN enabled. Tools will run automatically.")
                speak_text("Auto run enabled. Tools will run automatically.")
            continue
        
        # Voice command handling
        if user.lower().startswith("/voice"):
            opt = user.split()[-1].lower() if len(user.split())>1 else ""
            if opt == "off":
                stop_voice_activation()
            elif opt == "on":
                if voice_ready:
                    start_voice_activation()
                else:
                    print(Fore.RED + "❌ Voice capabilities not available." + Style.RESET_ALL)
            continue
        
        if user.lower() == "/listen":
            if voice_ready:
                print(Fore.YELLOW + "🎤 Listening for voice input..." + Style.RESET_ALL)
                speak_text("I'm listening. What can I help you with?")
                voice_input = listen_for_voice()
                if voice_input:
                    user = voice_input
                    print(Fore.GREEN + f"🎯 Voice command: {voice_input}" + Style.RESET_ALL)
                else:
                    print(Fore.YELLOW + "No voice input received." + Style.RESET_ALL)
                    continue
            else:
                print(Fore.RED + "❌ Voice capabilities not available." + Style.RESET_ALL)
                continue
        
        if user.lower() == "/test_voice":
            if voice_ready:
                print(Fore.YELLOW + "🎤 Testing voice recognition..." + Style.RESET_ALL)
                speak_text("Testing voice recognition. Please say something.")
                test_input = listen_for_voice()
                if test_input:
                    print(Fore.GREEN + f"🎯 Test successful! Heard: {test_input}" + Style.RESET_ALL)
                    speak_text(f"I heard you say: {test_input}")
                else:
                    print(Fore.YELLOW + "Test failed - no voice input detected." + Style.RESET_ALL)
                    speak_text("I didn't hear anything. Please try again.")
                continue
            else:
                print(Fore.RED + "❌ Voice capabilities not available." + Style.RESET_ALL)
                continue

        messages.append({"role":"user","content": user})
        
        # Debug: show what's being sent to model
        print(Fore.BLUE + f"🔄 Sending to AI model: {user}" + Style.RESET_ALL)
        
        # call model
        content, raw = call_model(messages)
        print(Fore.MAGENTA + "\n🧠 Thinking...\n" + Style.RESET_ALL)
        print(content)
        
        # Speak the response if voice is available
        if voice_ready:
            # Extract just the main response text (remove command blocks)
            clean_content = re.sub(r'<<COMMAND>>.*?<<END_COMMAND>>', '', content, flags=re.DOTALL).strip()
            if clean_content:
                speak_text(clean_content)
            else:
                # If no clean content, speak a brief acknowledgment
                speak_text("Working on it.")
        # extract commands
        cmds = extract_commands(content)
        print(Fore.BLUE + f"🔍 Extracted commands from AI: {cmds}" + Style.RESET_ALL)
        
        if not cmds:
            fb = detect_fallback(content)
            if fb: 
                cmds = [fb]
                print(Fore.BLUE + f"🔍 Using fallback command: {fb}" + Style.RESET_ALL)

        ran = False
        tool_results = []
        print(Fore.BLUE + f"🛠️ About to execute {len(cmds)} commands" + Style.RESET_ALL)
        
        for cmd in cmds:
            name = cmd.get("name")
            args = cmd.get("args", {}) or {}
            # confirm if autorun disabled
            if not AUTO_RUN:
                confirm = input(Fore.YELLOW + f"Run tool {name} with args {args}? (y/n): ").strip().lower()
                if confirm != "y":
                    print(Fore.RED + "Skipped.")
                    tool_results.append({"tool":name,"result":{"ok":False,"skipped":True}})
                    continue
            fn = TOOL_REGISTRY.get(name)
            if not fn:
                res = {"ok": False, "error": "unknown tool"}
                print(Fore.RED + f"Unknown tool: {name}")
            else:
                print(Fore.YELLOW + f"\n⚡ Executing tool: {name} {args}" + Style.RESET_ALL)
                res = fn(args) if args else fn()
                print(Fore.GREEN + f"✅ Tool result: {res}\n" + Style.RESET_ALL)
                
                # Speak tool result if voice is available
                if voice_ready and res.get("ok"):
                    action = res.get("action", "completed")
                    speak_text(f"Tool {name} {action}")
            tool_results.append({"tool":name,"result":res})
            log_tool_call(user, cmd, res)
            messages.append({"role":"system","content": f"Tool '{name}' executed. Result: {json.dumps(res)}"})
            ran = ran or (res.get("ok") is True)

        # If tools ran, ask model to summarize what it did (final answer)
        if ran:
            messages.append({"role":"user","content":"Summarize in one short sentence what you did and where outputs are."})
            content2, raw2 = call_model(messages)
            print(Fore.CYAN + "\n🤖 Final Answer:\n" + Style.RESET_ALL + content2 + "\n")
            
            # Speak the final answer
            if voice_ready:
                speak_text(content2)
            
            messages.append({"role":"assistant","content": content2})
        else:
            print(Fore.CYAN + "\n🤖 Final Answer:\n" + Style.RESET_ALL + content + "\n")
            messages.append({"role":"assistant","content": content})

if __name__ == "__main__":
    main()
