import sys
from pathlib import Path

def test_imports():
    print("1. Checking Python library imports...")
    required_packages = [
        ("fastapi", "fastapi"),
        ("uvicorn", "uvicorn"),
        ("spacy", "spacy"),
        ("whisper", "openai-whisper"),
        ("pandas", "pandas"),
        ("numpy", "numpy"),
        ("torch", "torch"),
        ("sklearn", "scikit-learn"),
        ("xgboost", "xgboost"),
        ("joblib", "joblib"),
        ("websockets", "websockets")
    ]
    
    missing = []
    for module_name, pkg_name in required_packages:
        try:
            __import__(module_name)
            print(f"  [PASS] {pkg_name} imported successfully")
        except ImportError:
            print(f"  [FAIL] {pkg_name} is missing!")
            missing.append(pkg_name)
            
    if missing:
        raise ImportError(f"Missing required packages: {', '.join(missing)}")

def test_spacy():
    print("\n2. Checking spaCy model loading...")
    import spacy
    try:
        nlp = spacy.load("en_core_web_sm")
        doc = nlp("Check if NLP extraction pipeline runs correctly.")
        print(f"  [PASS] spaCy model 'en_core_web_sm' loaded. Parsed tokens: {[token.text for token in doc]}")
    except Exception as e:
        print(f"  [FAIL] Failed to load spaCy model: {e}")
        raise e

def test_models():
    print("\n3. Checking pre-trained conversion models...")
    root = Path(__file__).resolve().parent
    model_path = root / "models" / "sales_conversion_model.pkl"
    features_path = root / "models" / "sales_conversion_features.pkl"
    metrics_path = root / "models" / "sales_conversion_metrics.json"
    lead_model_path = root / "data" / "processed" / "lead_scoring_model.joblib"
    
    paths = [
        ("Sales Conversion Model", model_path),
        ("Sales Conversion Features", features_path),
        ("Sales Conversion Metrics", metrics_path),
        ("Lead Scoring Model", lead_model_path)
    ]
    
    missing_files = []
    for name, path in paths:
        if path.exists():
            print(f"  [PASS] {name} exists at {path.name} ({path.stat().st_size} bytes)")
        else:
            print(f"  [FAIL] {name} is missing at {path}")
            missing_files.append(path.name)
            
    if missing_files:
        raise FileNotFoundError(f"Missing model files: {', '.join(missing_files)}")
        
    import joblib
    try:
        model = joblib.load(model_path)
        features = joblib.load(features_path)
        print("  [PASS] Successfully loaded XGBoost and Features metadata using joblib")
    except Exception as e:
        print(f"  [FAIL] Failed to load model files: {e}")
        raise e

if __name__ == "__main__":
    print("==================================================")
    print("   Nexus AI - System Integrity Verification Test  ")
    print("==================================================")
    try:
        test_imports()
        test_spacy()
        test_models()
        print("\nSUCCESS: All backend system checks passed!")
        sys.exit(0)
    except Exception as e:
        print(f"\nFAILURE: System validation failed! Error details:")
        print(f"  {e}")
        sys.exit(1)
