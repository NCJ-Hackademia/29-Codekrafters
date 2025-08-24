#!/usr/bin/env python3
"""
MediaPipe Installation Helper for Python 3.13
This script helps install mediapipe on Python 3.13 by trying different approaches
"""

import subprocess
import sys
import os

def run_command(cmd):
    """Run a command and return the result"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)

def main():
    print("🔍 MediaPipe Installation Helper for Python 3.13")
    print("=" * 50)
    
    print(f"Current Python version: {sys.version}")
    print(f"Python executable: {sys.executable}")
    
    # Try different installation methods
    methods = [
        ("Standard pip install", "pip install mediapipe"),
        ("Force reinstall", "pip install --force-reinstall mediapipe"),
        ("Install from PyPI directly", "pip install --index-url https://pypi.org/simple/ mediapipe"),
        ("Install with specific version", "pip install mediapipe==0.10.8"),
        ("Install from alternative source", "pip install --extra-index-url https://pypi.org/simple/ mediapipe"),
    ]
    
    for method_name, command in methods:
        print(f"\n🔄 Trying: {method_name}")
        print(f"Command: {command}")
        
        success, stdout, stderr = run_command(command)
        
        if success:
            print("✅ SUCCESS! MediaPipe installed successfully!")
            return True
        else:
            print(f"❌ Failed: {stderr.strip()}")
    
    print("\n❌ All installation methods failed!")
    print("\n💡 Solutions:")
    print("1. Install Python 3.11 or 3.12 (which support MediaPipe)")
    print("2. Use a virtual environment with Python 3.11/3.12")
    print("3. Wait for MediaPipe to support Python 3.13")
    print("4. Use alternative hand tracking libraries")
    
    return False

if __name__ == "__main__":
    main()
