import hashlib
import torch
import numpy as np
from src.aspect_sentiment.model_manager import ModelManager

_EMBEDDING_CACHE = {}

def get_speaker_embedding(samples: np.ndarray) -> np.ndarray:
    """
    Extract a 192-dimensional speaker embedding from raw audio samples using SpeechBrain ECAPA.
    Includes MD5 hashing and caching of speaker embeddings to optimize performance.
    """
    if len(samples) == 0:
        return np.zeros(192, dtype=np.float32)
        
    # Compute MD5 hash of sample bytes
    sample_hash = hashlib.md5(samples.tobytes()).hexdigest()
    if sample_hash in _EMBEDDING_CACHE:
        return _EMBEDDING_CACHE[sample_hash]
        
    # Ensure samples are float32
    samples_f32 = samples.astype(np.float32)
    
    # Get SpeechBrain classifier from ModelManager
    classifier = ModelManager().get_ecapa()
    
    # Convert to torch tensor with batch dimension (1, samples)
    tensor = torch.from_numpy(samples_f32).unsqueeze(0)
    
    with torch.no_grad():
        # Classifier returns shape (1, 1, 192) or similar
        emb = classifier.encode_batch(tensor)
        # Squeeze to shape (192,) and return as numpy array
        embedding = emb.squeeze().cpu().numpy()
        
    _EMBEDDING_CACHE[sample_hash] = embedding
    return embedding

