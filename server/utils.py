import os
import json
from typing import Dict, Any

def save_file_status(file_status: Dict[str, Dict[str, Any]], filepath: str = "file_status.json"):
    """Save the file status to a JSON file"""
    with open(filepath, 'w') as f:
        json.dump(file_status, f)

def load_file_status(filepath: str = "file_status.json") -> Dict[str, Dict[str, Any]]:
    """Load the file status from a JSON file"""
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            return json.load(f)
    return {}

def get_file_extension(filename: str) -> str:
    """Get the file extension from a filename"""
    return filename.split('.')[-1]

def is_video_file(filename: str) -> bool:
    """Check if a file is a video file based on its extension"""
    video_extensions = ['mp4', 'avi', 'mov', 'wmv', 'flv', 'mkv']
    ext = get_file_extension(filename).lower()
    return ext in video_extensions