import unittest
import asyncio
import numpy as np
from unittest.mock import patch, MagicMock, AsyncMock
from src.aspect_sentiment.embeddings import get_speaker_embedding, _EMBEDDING_CACHE
from src.aspect_sentiment.llama_extraction import call_llama, CACHE_DIR

class PerformanceOptimizationTests(unittest.TestCase):
    def setUp(self):
        # Clear caches before test
        _EMBEDDING_CACHE.clear()
        
    def test_speaker_embedding_caching(self):
        samples = np.array([0.1, 0.2, 0.3, 0.4], dtype=np.float32)
        
        # Mock ECAPA classifier to see if it is called
        mock_classifier = MagicMock()
        mock_classifier.encode_batch.return_value.squeeze.return_value.cpu.return_value.numpy.return_value = np.zeros(192, dtype=np.float32)
        
        with patch("src.aspect_sentiment.embeddings.ModelManager") as mock_mgr:
            mock_mgr.return_value.get_ecapa.return_value = mock_classifier
            
            # First call: should run the classifier
            emb1 = get_speaker_embedding(samples)
            self.assertEqual(len(emb1), 192)
            self.assertEqual(mock_classifier.encode_batch.call_count, 1)
            
            # Second call: should hit cache
            emb2 = get_speaker_embedding(samples)
            self.assertTrue(np.array_equal(emb1, emb2))
            self.assertEqual(mock_classifier.encode_batch.call_count, 1) # Still 1!

    @patch("httpx.AsyncClient.post", new_callable=AsyncMock)
    def test_llama_disk_caching(self, mock_post):
        # Set environment variable for LLaMA API key
        with patch.dict("os.environ", {"LLAMA_API_KEY": "test-key"}):
            # Clean cache directory if exists or delete mock cache keys
            messages = [{"role": "user", "content": "hello caching test"}]
            
            # Mock successful response
            mock_response = MagicMock()
            mock_response.json.return_value = {"choices": [{"message": {"content": '{"test": "ok"}'}}]}
            mock_response.raise_for_status = MagicMock()
            mock_post.return_value = mock_response
            
            # First call: should trigger POST request
            res1 = asyncio.run(call_llama(messages))
            self.assertEqual(res1["choices"][0]["message"]["content"], '{"test": "ok"}')
            self.assertEqual(mock_post.call_count, 1)
            
            # Second call: should read from disk cache (no POST request)
            res2 = asyncio.run(call_llama(messages))
            self.assertEqual(res2["choices"][0]["message"]["content"], '{"test": "ok"}')
            self.assertEqual(mock_post.call_count, 1) # Still 1!
            
            # Clean up the cache file
            import hashlib
            import json
            serialized = json.dumps(messages, sort_keys=True)
            cache_key = hashlib.md5(serialized.encode("utf-8")).hexdigest()
            cache_file = CACHE_DIR / f"{cache_key}.json"
            if cache_file.exists():
                cache_file.unlink()

if __name__ == "__main__":
    unittest.main()
