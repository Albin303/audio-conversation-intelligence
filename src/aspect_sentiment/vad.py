import torch
import numpy as np
from pathlib import Path
from typing import Any, Dict, List
from src.aspect_sentiment.model_manager import ModelManager
from src.aspect_sentiment.diarization import _load_audio_mono

def get_speech_segments(audio_path: Path) -> List[Dict[str, float]]:
    """
    Detect speech segments from an audio file using Silero VAD.
    Returns a list of dicts with 'start' and 'end' timestamps in seconds.
    """
    # Get VAD model and utilities from ModelManager
    model, utils = ModelManager().get_vad()
    get_speech_timestamps = utils[0]
    
    # Load audio as 16kHz mono float32
    samples, sample_rate = _load_audio_mono(audio_path)
    audio_tensor = torch.from_numpy(samples)
    
    # Get speech timestamps (samples indices)
    with torch.no_grad():
        timestamps = get_speech_timestamps(audio_tensor, model, sampling_rate=16000)
        
    segments = []
    for ts in timestamps:
        segments.append({
            "start": round(ts["start"] / 16000.0, 3),
            "end": round(ts["end"] / 16000.0, 3)
        })
    return segments
