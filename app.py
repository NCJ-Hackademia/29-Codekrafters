from flask import Flask, render_template, jsonify, request
import subprocess
import os
import sys
import logging
import json
import signal
import psutil
import threading
import time

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Global variables for voice processes
voice_command_process = None
voice_transcription_process = None

# Get the workspace root directory and script paths
WORKSPACE_ROOT = os.path.abspath(os.path.dirname(__file__))
SCRIPTS_DIR = os.path.join(WORKSPACE_ROOT, "virtual-controlls", "adaptive-ai")
COLLECT_SCRIPT = os.path.join(SCRIPTS_DIR,  "collect_gestures.py")
PREDICT_SCRIPT = os.path.join(SCRIPTS_DIR, "predict_live.py")
GESTURES_FILE = os.path.join(SCRIPTS_DIR, "custom_gestures.json")
MAPPINGS_FILE = os.path.join(SCRIPTS_DIR, "key_mappings.json")
MOUSE_CONTROLLER_SCRIPT = os.path.join(WORKSPACE_ROOT, "virtual-controlls", "edu-hcare.py")
AIR_CONTROLLER_SCRIPT = os.path.join(WORKSPACE_ROOT, "virtual-controlls", "air-controller.py")

# Voice recognition scripts
VOICE_DIR = os.path.join(WORKSPACE_ROOT, "Voice-auto")
VOICE_MODEL_PATH = os.path.join(VOICE_DIR, "vosk-model-small-en-us-0.15")
VOICE_COMMANDS_FILE = os.path.join(VOICE_DIR, "commands.json")

# Default commands and their descriptions
DEFAULT_COMMANDS = {
    "stop": {"function": "Stop current operation", "trained": False, "default": True},
    "left": {"function": "Navigate left (default: LEFT arrow key)", "trained": False, "default": True, "key": "LEFT"},
    "right": {"function": "Navigate right (default: RIGHT arrow key)", "trained": False, "default": True, "key": "RIGHT"},
    "up": {"function": "Navigate up (default: UP arrow key)", "trained": False, "default": True, "key": "UP"},
    "down": {"function": "Navigate down (default: DOWN arrow key)", "trained": False, "default": True, "key": "DOWN"},
    "none": {"function": "No action", "trained": False, "default": True},
    "undo": {"function": "Undo last action (default: CTRL+Z)", "trained": False, "default": True, "key": "CTRL+Z"},
    "redo": {"function": "Redo last action (default: CTRL+Y)", "trained": False, "default": True, "key": "CTRL+Y"}
}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_voice_commands')
def get_voice_commands():
    try:
        if os.path.exists(VOICE_COMMANDS_FILE):
            with open(VOICE_COMMANDS_FILE, 'r') as f:
                commands = json.load(f)
            return jsonify({"status": "success", "commands": commands})
        else:
            return jsonify({"status": "error", "message": "Commands file not found"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/get_gestures')
def get_gestures():
    try:
        gestures = DEFAULT_COMMANDS.copy()
        if os.path.exists(GESTURES_FILE):
            with open(GESTURES_FILE, 'r') as f:
                custom_gestures = json.load(f)
                gestures.update(custom_gestures)
        
        # Load key mappings if they exist
        key_mappings = {}
        if os.path.exists(MAPPINGS_FILE):
            with open(MAPPINGS_FILE, 'r') as f:
                key_mappings = json.load(f)
        
        # Update gestures with custom key mappings
        for gesture_name, mapping in key_mappings.items():
            if gesture_name in gestures:
                gestures[gesture_name]['key'] = mapping
        
        return jsonify({"status": "success", "gestures": gestures})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/update_mapping', methods=['POST'])
def update_mapping():
    try:
        data = request.json
        gesture_name = data.get('gesture')
        new_key = data.get('key')
        
        if not gesture_name or not new_key:
            return jsonify({
                "status": "error",
                "message": "Gesture name and key mapping are required"
            })
        
        # Load existing mappings
        mappings = {}
        if os.path.exists(MAPPINGS_FILE):
            with open(MAPPINGS_FILE, 'r') as f:
                mappings = json.load(f)
        
        # Update mapping
        mappings[gesture_name] = new_key
        
        # Save mappings
        with open(MAPPINGS_FILE, 'w') as f:
            json.dump(mappings, f, indent=4)
        
        return jsonify({
            "status": "success",
            "message": f"Updated key mapping for {gesture_name} to {new_key}"
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/start_training', methods=['POST'])
def start_training():
    try:
        gesture_data = request.json
        gesture_name = gesture_data.get('name', '').strip()
        gesture_function = gesture_data.get('function', '').strip()
        
        if not gesture_name or not gesture_function:
            return jsonify({
                "status": "error",
                "message": "Gesture name and function are required"
            })

        # Save gesture details to JSON file
        gestures = {}
        if os.path.exists(GESTURES_FILE):
            with open(GESTURES_FILE, 'r') as f:
                gestures = json.load(f)
        
        gestures[gesture_name] = {
            "function": gesture_function,
            "trained": False,
            "default": False
        }
        
        with open(GESTURES_FILE, 'w') as f:
            json.dump(gestures, f, indent=4)

        # Run collect_gestures.py with the gesture name
        process = subprocess.Popen(
            [sys.executable, COLLECT_SCRIPT, "--gesture", gesture_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=SCRIPTS_DIR
        )
        logger.info(f"Started training process for gesture: {gesture_name}")
        return jsonify({
            "status": "success",
            "message": f"Training process started for gesture: {gesture_name}"
        })
    except Exception as e:
        logger.error(f"Error starting training: {str(e)}")
        return jsonify({"status": "error", "message": str(e)})

@app.route('/start_prediction')
def start_prediction():
    try:
        process = subprocess.Popen(
            [sys.executable, PREDICT_SCRIPT],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=SCRIPTS_DIR
        )
        logger.info(f"Started prediction process with PID: {process.pid}")
        return jsonify({
            "status": "success",
            "message": "Prediction process started",
            "pid": process.pid
        })
    except Exception as e:
        logger.error(f"Error starting prediction: {str(e)}")
        return jsonify({"status": "error", "message": str(e)})

@app.route('/start_mouse_controller', methods=['GET', 'POST'])
def start_mouse_controller():
    try:
        # Check if Python is in PATH
        python_cmd = sys.executable
        
        # Set creation flags based on platform
        kwargs = {}
        if os.name == 'nt':  # Windows
            kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
        
        # Check if the script exists
        if not os.path.exists(MOUSE_CONTROLLER_SCRIPT):
            logger.error(f"Mouse controller script not found at: {MOUSE_CONTROLLER_SCRIPT}")
            return jsonify({
                'status': 'error',
                'message': f'Mouse controller script not found at: {MOUSE_CONTROLLER_SCRIPT}'
            })
        
        # Run the script with appropriate working directory
        process = subprocess.Popen(
            [python_cmd, MOUSE_CONTROLLER_SCRIPT],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=os.path.dirname(MOUSE_CONTROLLER_SCRIPT),
            **kwargs
        )
        
        logger.info(f"Started mouse controller process with PID: {process.pid}")
        return jsonify({
            'status': 'success',
            'message': 'Mouse controller started',
            'pid': process.pid
        })
    except Exception as e:
        logger.error(f"Error starting mouse controller: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Error starting mouse controller: {str(e)}'
        })

@app.route('/start_air_controller', methods=['GET', 'POST'])
def start_air_controller():
    try:
        # Check if Python is in PATH
        python_cmd = sys.executable
        
        # Set creation flags based on platform
        kwargs = {}
        if os.name == 'nt':  # Windows
            kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
        
        # Check if the script exists
        if not os.path.exists(AIR_CONTROLLER_SCRIPT):
            # If the script doesn't exist, fall back to the mouse controller
            logger.warning(f"Air controller script not found at: {AIR_CONTROLLER_SCRIPT}, falling back to mouse controller")
            
            # Just create a copy of edu-hcare.py as air-controller.py
            air_controller_dir = os.path.dirname(AIR_CONTROLLER_SCRIPT)
            os.makedirs(air_controller_dir, exist_ok=True)
            
            with open(MOUSE_CONTROLLER_SCRIPT, 'r') as src_file:
                content = src_file.read()
            
            with open(AIR_CONTROLLER_SCRIPT, 'w') as dst_file:
                dst_file.write(content)
            
            logger.info(f"Created air controller script at: {AIR_CONTROLLER_SCRIPT}")
        
        # Run the script with appropriate working directory
        process = subprocess.Popen(
            [python_cmd, AIR_CONTROLLER_SCRIPT],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=os.path.dirname(AIR_CONTROLLER_SCRIPT),
            **kwargs
        )
        
        logger.info(f"Started air controller process with PID: {process.pid}")
        return jsonify({
            'status': 'success',
            'message': 'Air controller started for gaming',
            'pid': process.pid
        })
    except Exception as e:
        logger.error(f"Error starting air controller: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Error starting air controller: {str(e)}'
        })

@app.route('/start_voice_command')
def start_voice_command():
    global voice_command_process
    try:
        # Check if model exists
        if not os.path.exists(VOICE_MODEL_PATH):
            return jsonify({
                "status": "error",
                "message": f"Voice model not found at: {VOICE_MODEL_PATH}"
            })
            
        # Stop any existing voice processes
        if voice_command_process and voice_command_process.poll() is None:
            for child in psutil.Process(voice_command_process.pid).children(recursive=True):
                child.terminate()
            voice_command_process.terminate()
        
        # Start the voice command process
        voice_command_script = os.path.join(VOICE_DIR, "final-model.py")
        voice_command_process = subprocess.Popen(
            [sys.executable, voice_command_script],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=VOICE_DIR
        )
        logger.info(f"Started voice command process with PID: {voice_command_process.pid}")
        return jsonify({
            "status": "success",
            "message": "Voice command process started",
            "pid": voice_command_process.pid
        })
    except Exception as e:
        logger.error(f"Error starting voice command: {str(e)}")
        return jsonify({"status": "error", "message": str(e)})

@app.route('/start_voice_transcription')
def start_voice_transcription():
    global voice_transcription_process
    try:
        # Stop any existing voice processes
        if voice_transcription_process and voice_transcription_process.poll() is None:
            try:
                for child in psutil.Process(voice_transcription_process.pid).children(recursive=True):
                    child.terminate()
                voice_transcription_process.terminate()
                # Wait a moment to ensure process is fully terminated
                time.sleep(1)
            except Exception as e:
                logger.error(f"Error stopping existing voice transcription process: {str(e)}")
        
        # Start the new simple voice typing process
        voice_transcription_script = os.path.join(VOICE_DIR, "simple_voice_typing.py")
        
        # Use creationflags to ensure the process has proper window focus permissions on Windows
        creation_flags = 0
        if os.name == 'nt':  # Windows
            creation_flags = subprocess.CREATE_NO_WINDOW
        
        voice_transcription_process = subprocess.Popen(
            [sys.executable, voice_transcription_script],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=VOICE_DIR,
            creationflags=creation_flags
        )
        
        # Log process info
        logger.info(f"Started voice typing process with PID: {voice_transcription_process.pid}")
        logger.info(f"Voice typing is now active. Speak to type text in your active application.")
        
        return jsonify({
            "status": "success",
            "message": "Voice typing process started. Click in a text area and start speaking.",
            "pid": voice_transcription_process.pid
        })
    except Exception as e:
        logger.error(f"Error starting voice typing: {str(e)}")
        return jsonify({"status": "error", "message": str(e)})

@app.route('/stop_process', methods=['POST'])
def stop_process():
    try:
        data = request.json
        pid = data.get('pid')
        process_type = data.get('type', 'unknown')
        
        if not pid:
            return jsonify({
                "status": "error",
                "message": "Process ID is required"
            })
        
        logger.info(f"Attempting to stop {process_type} process with PID: {pid}")
        
        # Check if process exists
        try:
            pid = int(pid)
            process = psutil.Process(pid)
            
            # First try to kill the process and its children gracefully
            try:
                children = process.children(recursive=True)
                for child in children:
                    try:
                        child.terminate()
                        logger.info(f"Terminated child process with PID: {child.pid}")
                    except Exception as child_e:
                        logger.warning(f"Error terminating child process {child.pid}: {str(child_e)}")
                        try:
                            child.kill()
                            logger.info(f"Killed child process with PID: {child.pid}")
                        except Exception as kill_e:
                            logger.error(f"Failed to kill child process {child.pid}: {str(kill_e)}")
                
                # Now terminate the main process
                process.terminate()
                process.wait(timeout=3)  # Wait for process to terminate
                logger.info(f"Successfully terminated process {pid}")
            except psutil.TimeoutExpired:
                # If termination times out, try to kill the process
                logger.warning(f"Process {pid} did not terminate gracefully, attempting to kill")
                process.kill()
                process.wait(timeout=3)
                logger.info(f"Successfully killed process {pid}")
            
            # Reset global variables if needed
            global voice_command_process, voice_transcription_process
            if process_type == 'voice_command' and voice_command_process and voice_command_process.pid == pid:
                voice_command_process = None
                logger.info("Reset voice_command_process to None")
            elif process_type == 'voice_transcription' and voice_transcription_process and voice_transcription_process.pid == pid:
                voice_transcription_process = None
                logger.info("Reset voice_transcription_process to None")
            
            return jsonify({
                "status": "success",
                "message": f"Process {pid} stopped successfully"
            })
        except psutil.NoSuchProcess:
            logger.warning(f"Process {pid} does not exist or was already terminated")
            return jsonify({
                "status": "success",
                "message": f"Process {pid} does not exist or was already terminated"
            })
        except psutil.AccessDenied as e:
            logger.error(f"Access denied when stopping process {pid}: {str(e)}")
            return jsonify({
                "status": "error",
                "message": f"Access denied when stopping process {pid}. This may be a system process that cannot be terminated."
            })
        except Exception as e:
            logger.error(f"Error stopping process {pid}: {str(e)}")
            return jsonify({
                "status": "error",
                "message": f"Error stopping process {pid}: {str(e)}"
            })
    except Exception as e:
        logger.error(f"Error processing stop request: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Error processing stop request: {str(e)}"
        })

@app.route('/stop_all_voice_processes')
def stop_all_voice_processes():
    global voice_command_process, voice_transcription_process
    try:
        stopped_count = 0
        
        # Stop voice command process if running
        if voice_command_process and voice_command_process.poll() is None:
            try:
                process = psutil.Process(voice_command_process.pid)
                for child in process.children(recursive=True):
                    child.terminate()
                process.terminate()
                voice_command_process = None
                stopped_count += 1
                logger.info(f"Stopped voice command process")
            except (psutil.NoSuchProcess, Exception) as e:
                logger.error(f"Error stopping voice command process: {str(e)}")
        
        # Stop voice transcription process if running
        if voice_transcription_process and voice_transcription_process.poll() is None:
            try:
                process = psutil.Process(voice_transcription_process.pid)
                for child in process.children(recursive=True):
                    child.terminate()
                process.terminate()
                voice_transcription_process = None
                stopped_count += 1
                logger.info(f"Stopped voice transcription process")
            except (psutil.NoSuchProcess, Exception) as e:
                logger.error(f"Error stopping voice transcription process: {str(e)}")
        
        return jsonify({
            "status": "success",
            "message": f"Stopped {stopped_count} voice processes"
        })
    except Exception as e:
        logger.error(f"Error stopping voice processes: {str(e)}")
        return jsonify({"status": "error", "message": str(e)})

@app.route('/update_voice_command', methods=['POST'])
def update_voice_command():
    try:
        data = request.json
        command_key = data.get('command')
        variants = data.get('variants')
        
        if not command_key or not variants or not isinstance(variants, list):
            return jsonify({
                "status": "error",
                "message": "Command key and variants list are required"
            })
        
        # Load existing commands
        commands = {}
        if os.path.exists(VOICE_COMMANDS_FILE):
            with open(VOICE_COMMANDS_FILE, 'r') as f:
                commands = json.load(f)
        
        # Update command
        commands[command_key] = variants
        
        # Save commands
        with open(VOICE_COMMANDS_FILE, 'w') as f:
            json.dump(commands, f, indent=4)
        
        return jsonify({
            "status": "success",
            "message": f"Updated voice command '{command_key}'"
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

if __name__ == '__main__':
    logger.info("Starting Paraso - Professional Gesture Control Interface")
    logger.info("Access the application at http://127.0.0.1:5000")
    app.run(debug=True, host='127.0.0.1', port=5000)