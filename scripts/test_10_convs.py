import sys
from pathlib import Path
import time
import json
import os
import asyncio

# Ensure the root directory is in the python path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Load local envs manually to ensure API keys are loaded
from src.api.server import load_env_file
load_env_file(ROOT / ".env.local")
load_env_file(ROOT / ".env")

from src.aspect_sentiment import AspectSentimentEngine
from src.api.server import predict_with_trained_model, fallback_extraction
from src.aspect_sentiment.llama_extraction import process_text

def main():
    data_dir = ROOT / "data" / "raw"
    engine = AspectSentimentEngine()
    
    results = []
    total_latency = 0
    
    print(f"Testing 10 conversations using Llama model: {engine.llama_model}\n")
    
    for i in range(1, 11):
        filename = f"conv_{i:03d}.txt"
        file_path = data_dir / filename
        
        if not file_path.exists():
            print(f"Skipping {filename} - not found")
            continue
            
        text = file_path.read_text(encoding="utf-8", errors="replace")
        
        start = time.perf_counter()
        
        # Analyze using engine
        try:
            # We use analyze_text for end-to-end testing
            response = asyncio.run(engine.analyze_text(
                text=text,
                source_name=filename,
                source_type="text",
                language="en",
                transcription_confidence=None,
                whisper_model=None,
                pipeline=[],
                processing_ms=0
            ))
            latency = time.perf_counter() - start
            total_latency += latency
            
            summary = response.summary
            conversion = response.conversionScore
            
            res = {
                "file": filename,
                "latency_s": round(latency, 2),
                "dominant_sentiment": summary.dominant,
                "conversion_prediction": conversion.label if conversion else "N/A",
                "conversion_prob": f"{conversion.probability:.2f}" if conversion else "N/A",
                "total_features_extracted": summary.totalProducts,
                "top_products": [p.name for p in response.products[:3]],
                "status": "Success"
            }
        except Exception as e:
            res = {
                "file": filename,
                "status": f"Failed: {str(e)}"
            }
        
        results.append(res)
        print(f"Processed {filename} in {res.get('latency_s', 0)}s - Conversion: {res.get('conversion_prediction', 'N/A')}")
        
    print(f"\nAverage Latency: {total_latency / 10:.2f}s")
    
    output_path = ROOT / "test_10_results.json"
    output_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"Full results written to {output_path}")

if __name__ == '__main__':
    main()
