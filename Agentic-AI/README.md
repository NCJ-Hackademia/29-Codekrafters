# 🚀 Voice Agent Final v8 - AI-Powered Desktop Automation

Your AI assistant that can control your computer and perform automated tasks through natural language commands!

## ✨ What's New

**From just screenshots to 50+ powerful desktop automation tools!**

- 🌐 **Browser & Tab Management** - Open Chrome, switch tabs, navigate
- 🖥️ **App Management** - Switch between apps, manage windows
- 📁 **System Apps** - Open Explorer, Notepad, Calculator, Camera
- 🚀 **Universal App Launcher** - Open any app by name
- 📸 **Camera Access** - Open camera app for taking pictures
- ✂️ **File Operations** - Copy, paste, cut, undo, redo, save
- 🔍 **View Controls** - Zoom in/out, reset zoom
- ⚙️ **System Controls** - Lock screen, show desktop, task manager
- 🔊 **Enhanced Media Controls** - Windows API volume control, media keys
- 💡 **Display Controls** - Brightness up/down

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Set Your Ollama Model
```bash
$env:OLLAMA_MODEL="chat_gemma1b_think"
```

### 3. Run the AI Assistant
```bash
python agent_cmds.py
```

### 4. Chat Naturally!
Just type what you want:
- "open chrome for me"
- "take a screenshot"
- "switch to the next tab"
- "copy this text"
- "open notepad"
- "minimize this window"
- "turn up the volume"
- "open camera for me"
- "open app spotify"
- "take a picture"

## 🧠 How It Works

1. **Natural Language Understanding** - The AI understands your requests
2. **Command Detection** - Automatically detects what tool to use
3. **Tool Execution** - Runs the appropriate desktop automation tool
4. **Response & Logging** - Gives you feedback and logs all actions

## 🛠️ Available Commands

### Browser & Tab Management
| Command | What It Does |
|---------|--------------|
| `open chrome` | Opens Google Chrome browser |
| `switch tab` | Switches to next tab (Ctrl+Tab) |
| `switch tab back` | Switches to previous tab |
| `close tab` | Closes current tab (Ctrl+W) |
| `new tab` | Opens new tab (Ctrl+T) |
| `refresh page` | Refreshes current page (F5) |
| `go back` | Goes back in browser (Alt+Left) |
| `go forward` | Goes forward in browser (Alt+Right) |

### App Management
| Command | What It Does |
|---------|--------------|
| `switch app` | Switches between applications (Alt+Tab) |
| `minimize window` | Minimizes current window |
| `maximize window` | Maximizes current window |
| `close window` | Closes current window (Alt+F4) |

### System Apps
| Command | What It Does |
|---------|--------------|
| `open explorer` | Opens File Explorer |
| `open notepad` | Opens Notepad |
| `open calculator` | Opens Calculator |
| `open camera` | Opens Windows Camera app for taking pictures |
| `open app <name>` | Opens any application by name (e.g., "open app spotify") |

### File Operations
| Command | What It Does |
|---------|--------------|
| `copy` | Copy selection (Ctrl+C) |
| `paste` | Paste (Ctrl+V) |
| `cut` | Cut selection (Ctrl+X) |
| `undo` | Undo (Ctrl+Z) |
| `redo` | Redo (Ctrl+Y) |
| `select all` | Select all (Ctrl+A) |
| `save` | Save (Ctrl+S) |
| `open file` | Open file dialog (Ctrl+O) |
| `print` | Print dialog (Ctrl+P) |
| `find` | Find dialog (Ctrl+F) |
| `replace` | Replace dialog (Ctrl+H) |

### View Controls
| Command | What It Does |
|---------|--------------|
| `zoom in` | Zoom in (Ctrl+Plus) |
| `zoom out` | Zoom out (Ctrl+Minus) |
| `reset zoom` | Reset zoom (Ctrl+0) |

### System Controls
| Command | What It Does |
|---------|--------------|
| `lock screen` | Lock the screen (Win+L) |
| `show desktop` | Show desktop (Win+D) |
| `task manager` | Open Task Manager (Ctrl+Shift+Esc) |
| `run dialog` | Open Run dialog (Win+R) |
| `settings` | Open Windows Settings (Win+I) |
| `action center` | Open Action Center (Win+A) |
| `search` | Open Windows Search (Win+S) |

### Media Controls
| Command | What It Does |
|---------|--------------|
| `volume up` | Increase volume (Windows API, 10% increments) |
| `volume down` | Decrease volume (Windows API, 10% increments) |
| `mute` | Mute/unmute volume (Windows API) |
| `play pause` | Play/pause media (multiple methods) |
| `next track` | Next media track (multiple methods) |
| `previous track` | Previous media track (multiple methods) |

### Display Controls
| Command | What It Does |
|---------|--------------|
| `brightness up` | Increase brightness |
| `brightness down` | Decrease brightness |

### Original Tools
| Command | What It Does |
|---------|--------------|
| `take screenshot` | Takes a screenshot |
| `press key` | Presses a specific key |
| `welcome home` | Shows welcome info |

## 🔧 Advanced Features

### Auto-run Toggle
- `/autorun on` - Tools run automatically
- `/autorun off` - Confirm each tool execution
- Default: Auto-run enabled

### Command History
All tool executions are logged to `logs/tool_calls.jsonl`

### Screenshots
Screenshots are saved to `screenshots/` folder with timestamps

## 📁 Project Structure

```
voice-agent-final-v8/
├── agent_cmds.py          # Main AI assistant with all tools
├── chat.py               # Reliable chat interface
├── chat_with_model.py    # Streaming chat interface
├── Modelfile             # AI model configuration
├── requirements.txt      # Python dependencies
├── demo_commands.py      # Demo of all tools
├── demo_chatbot.py      # Demo of chatbot integration
├── test_tools.py         # Test all tools
├── COMMANDS_REFERENCE.md # Complete command reference
├── screenshots/          # Screenshot storage
└── logs/                 # Tool execution logs
```

## 🎯 Examples

### Basic Usage
```
You: open chrome for me
🧠 Thinking...
I need to open Google Chrome browser for the user.

⚡ Executing tool: open_chrome {}
✅ Tool result: {'ok': True, 'action': 'opened_chrome', 'path': 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'}

🤖 Final Answer: I've opened Google Chrome for you.
```

### Complex Workflow
```
You: take a screenshot and then open notepad
🧠 Thinking...
The user wants me to capture a screenshot and then open Notepad.

⚡ Executing tool: take_screenshot {}
✅ Tool result: {'ok': True, 'path': 'screenshots/screenshot_20241224_143022.png'}

⚡ Executing tool: open_notepad {}
✅ Tool result: {'ok': True, 'action': 'opened_notepad'}

🤖 Final Answer: I've taken a screenshot and opened Notepad for you.
```

## 🚨 Safety Features

- **Safe Key Whitelist** - Only allows safe keyboard shortcuts
- **Command Whitelist** - Only allows safe shell commands
- **Error Handling** - Graceful failure for all tools
- **Logging** - All actions are logged for audit

## 🔍 Troubleshooting

### Common Issues

1. **"Unknown tool" error**
   - Make sure you're using the latest version
   - Check that all dependencies are installed

2. **Tool not working**
   - Verify the tool exists in `TOOL_REGISTRY`
   - Check the tool's error message

3. **Ollama connection issues**
   - Ensure Ollama is running: `ollama serve`
   - Check your model is available: `ollama list`

### Dependencies
Make sure you have:
- Python 3.7+
- All packages in `requirements.txt`
- Ollama running locally
- Windows 10/11 (for Windows-specific tools)

## 🎉 What You Can Do Now

✅ **Open any application** with natural language  
✅ **Control your browser** - tabs, navigation, refresh  
✅ **Manage windows** - minimize, maximize, close  
✅ **File operations** - copy, paste, save, find  
✅ **System control** - lock screen, task manager, settings  
✅ **Media control** - volume, play/pause, brightness  
✅ **Take screenshots** automatically  
✅ **Chat naturally** - no need to remember commands  

## 🚀 Ready to Use!

Your AI desktop assistant is ready! Just run:

```bash
$env:OLLAMA_MODEL="chat_gemma1b_think"
python agent_cmds.py
```

Then start chatting with your computer! 🎯✨
