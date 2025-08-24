# 🚀 Paraso - Professional Gesture & Voice Control System

A cutting-edge desktop automation system that combines gesture recognition, voice commands, and AI-powered automation to create an intuitive and powerful computer control experience.

## 🌟 Features

### 🤖 **Agentic AI Integration**
- **Voice-Activated AI Assistant**: Say "hey jarvis" to activate voice commands
- **Desktop Automation**: Take screenshots, open applications, control system settings
- **Natural Language Processing**: Understand and execute complex commands
- **Persistent Console Interface**: Interactive AI agent with real-time feedback

### 🖐️ **Advanced Gesture Recognition**
- **8 Gesture Types**: Up, Down, Left, Right, Stop, Undo, Redo, None
- **Machine Learning Model**: Trained on 750+ gesture samples
- **Real-time Processing**: Instant gesture recognition and response
- **Customizable Mappings**: Configurable key bindings for each gesture

### 🎮 **Virtual Controls**
- **Air Controller**: Gesture-based gaming controls
- **Adaptive AI**: Self-improving gesture recognition system
- **Data Collection**: Built-in gesture training and data collection tools
- **Model Training**: Automated machine learning pipeline

### 🎨 **Modern Web Interface**
- **Responsive Design**: Works on desktop and mobile devices
- **Real-time Feedback**: Live gesture detection and status updates
- **Process Management**: Start/stop individual components
- **Professional UI**: Clean, modern interface with dark theme

## 🛠️ Installation

### Prerequisites
- Python 3.11 or higher
- Windows 10/11 (primary support)
- Webcam for gesture recognition
- Microphone for voice commands

### Setup Instructions

1. **Clone the Repository**
   ```bash
   git clone https://github.com/vigneshbs33/29-Codekrafters.git
   cd 29-Codekrafters
   ```

2. **Install Dependencies**
   ```bash
   # Install MediaPipe and core dependencies
   python install_mediapipe.py
   
   # Activate virtual environment
   mediapipe_env\Scripts\activate
   
   # Install additional requirements
   pip install -r requirements.txt
   pip install -r Agentic-AI/requirements.txt
   ```

3. **Install Agentic AI Dependencies**
   ```bash
   cd Agentic-AI
   pip install SpeechRecognition PyAudio pycaw mss
   cd ..
   ```

## 🚀 Usage

### Starting the Application

1. **Activate Virtual Environment**
   ```bash
   mediapipe_env\Scripts\activate
   ```

2. **Run the Flask Application**
   ```bash
   python app.py
   ```

3. **Access the Web Interface**
   - Open your browser and go to `http://localhost:5000`
   - The interface will show all available controls

### Using the System

#### **Gesture Controls**
- **Start Gesture Recognition**: Click "Start Gesture Recognition"
- **Available Gestures**:
  - 👆 **Up**: Navigate up or increase values
  - 👇 **Down**: Navigate down or decrease values
  - 👈 **Left**: Navigate left or previous
  - 👉 **Right**: Navigate right or next
  - ✋ **Stop**: Stop current action
  - ↩️ **Undo**: Undo last action
  - 🔄 **Redo**: Redo last action
  - 🚫 **None**: No action

#### **Voice AI Assistant**
- **Activate**: Click "Call Agent (Opens Console)"
- **Wake Word**: Say "hey jarvis" to activate
- **Commands**: 
  - "take a screenshot"
  - "open chrome"
  - "increase volume"
  - "what time is it"
  - And many more...

#### **Air Controller**
- **Start**: Click "Start Air Controller"
- **Gaming Controls**: Use gestures for gaming input
- **Customizable**: Configure gesture-to-key mappings

## 📁 Project Structure

```
Paraso/
├── app.py                          # Main Flask application
├── requirements.txt                # Python dependencies
├── install_mediapipe.py           # MediaPipe installation script
├── templates/                     # Web interface templates
│   ├── index.html                # Main interface
│   ├── css/                      # Stylesheets
│   └── js/                       # JavaScript files
├── Agentic-AI/                   # AI voice assistant
│   ├── agent_cmds.py            # Main AI agent script
│   ├── requirements.txt         # AI dependencies
│   └── README.md               # AI documentation
├── virtual-controlls/           # Gesture recognition system
│   ├── adaptive-ai/            # Machine learning components
│   │   ├── DATA/              # Training data
│   │   ├── models/            # Trained ML models
│   │   └── collect_gestures.py # Data collection tool
│   └── air-controller.py      # Gaming controller
└── mediapipe_env/              # Virtual environment
```

## 🔧 Configuration

### Gesture Mappings
Edit `virtual-controlls/adaptive-ai/key_mappings.json` to customize gesture-to-key mappings:

```json
{
  "up": "w",
  "down": "s", 
  "left": "a",
  "right": "d",
  "stop": "space",
  "undo": "ctrl+z",
  "redo": "ctrl+y"
}
```

### Voice Commands
The AI agent supports natural language commands for:
- **System Control**: Volume, brightness, power management
- **Application Launch**: Open programs, websites, files
- **Screenshots**: Capture screen, specific windows, or regions
- **Information**: Time, date, system status
- **Custom Actions**: User-defined automation tasks

## 🤝 Contributing

This project is part of **Hackademia 2025 - Codekrafters** hackathon. 

### Team Information
- **Team Name**: Codekrafters
- **Team Captain**: @vigneshbs33
- **Repository**: 29-Codekrafters

### Development Guidelines
- Follow hackathon rules and guidelines
- Maintain code quality and documentation
- Test features thoroughly before committing
- Respect the 60% AI-generated code limit

## 📝 License

This project is developed for the Hackademia 2025 hackathon hosted by National College Jayanagar.

## 🎯 Future Enhancements

- [ ] Multi-language voice support
- [ ] Advanced gesture combinations
- [ ] Cloud-based AI processing
- [ ] Mobile app companion
- [ ] Integration with smart home devices
- [ ] Custom gesture training interface
- [ ] Performance optimization
- [ ] Cross-platform support

## 🐛 Troubleshooting

### Common Issues

1. **ModuleNotFoundError**: Ensure virtual environment is activated
2. **Camera Access**: Grant camera permissions to the application
3. **Microphone Issues**: Check microphone permissions and settings
4. **Gesture Recognition**: Ensure good lighting and clear hand movements

### Support
For issues and questions, please refer to the hackathon organizers or create an issue in the repository.

---

**Built by Team Codekrafters for Hackademia 2025**
