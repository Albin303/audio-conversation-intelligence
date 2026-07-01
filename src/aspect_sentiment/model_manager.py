import os
import threading
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

class ModelManager:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super(ModelManager, cls).__new__(cls)
                    cls._instance._init_models()
        return cls._instance

    def _init_models(self):
        self._models = {}
        self._locks = {
            "vad": threading.Lock(),
            "ecapa": threading.Lock(),
            "minilm": threading.Lock(),
            "spacy": threading.Lock(),
            "xgboost": threading.Lock(),
            "whisper": threading.Lock()
        }

    def get_vad(self):
        if "vad" not in self._models:
            with self._locks["vad"]:
                if "vad" not in self._models:
                    import torch

                    # Load Silero VAD model
                    model, utils = torch.hub.load(
                        repo_or_dir='snakers4/silero-vad',
                        model='silero_vad',
                        force_reload=False,
                        trust_repo=True
                    )
                    torch.set_num_threads(1)
                    self._models["vad"] = (model, utils)
        return self._models["vad"]

    def get_ecapa(self):
        if "ecapa" not in self._models:
            with self._locks["ecapa"]:
                if "ecapa" not in self._models:
                    from speechbrain.inference.speaker import EncoderClassifier

                    # Load SpeechBrain ECAPA model
                    savedir = os.path.join(os.path.expanduser("~"), ".cache", "speechbrain")
                    model_source = os.getenv("SPEECHBRAIN_MODEL", "speechbrain/spkrec-ecapa-voxceleb")
                    classifier = EncoderClassifier.from_hparams(
                        source=model_source,
                        run_opts={"device": "cpu"},
                        savedir=savedir
                    )
                    self._models["ecapa"] = classifier
        return self._models["ecapa"]

    def get_minilm(self):
        if "minilm" not in self._models:
            with self._locks["minilm"]:
                if "minilm" not in self._models:
                    from sentence_transformers import SentenceTransformer

                    # Load SentenceTransformer MiniLM model
                    self._models["minilm"] = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
        return self._models["minilm"]

    def get_spacy(self):
        if "spacy" not in self._models:
            with self._locks["spacy"]:
                if "spacy" not in self._models:
                    import spacy

                    # Load spaCy NLP model
                    for model_name in ("en_core_web_sm", "en_core_web_md"):
                        try:
                            self._models["spacy"] = spacy.load(model_name)
                            break
                        except OSError:
                            continue
                    else:
                        nlp = spacy.blank("en")
                        if "sentencizer" not in nlp.pipe_names:
                            nlp.add_pipe("sentencizer")
                        self._models["spacy"] = nlp
        return self._models["spacy"]

    def get_xgboost(self):
        if "xgboost" not in self._models:
            with self._locks["xgboost"]:
                if "xgboost" not in self._models:
                    import joblib

                    # Load XGBoost conversion model
                    model_path = REPO_ROOT / "models" / "sales_conversion_model.pkl"
                    self._models["xgboost"] = joblib.load(model_path)
        return self._models["xgboost"]

    def get_whisper(self, model_size="small", device="cpu"):
        key = f"whisper_{model_size}_{device}"
        if key not in self._models:
            with self._locks["whisper"]:
                if key not in self._models:
                    import whisper
                    self._models[key] = whisper.load_model(model_size, device=device)
        return self._models[key]
