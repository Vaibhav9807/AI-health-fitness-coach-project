"""Load a validated dataset model for an informational score estimate."""
from functools import lru_cache
from pathlib import Path
import joblib
import pandas as pd

MODEL_PATH=Path(__file__).resolve().parents[1]/"models"/"fitness_level.joblib"


class ModelUnavailable(RuntimeError):
    pass


@lru_cache(maxsize=1)
def _load():
    if not MODEL_PATH.is_file():
        raise ModelUnavailable("No validated fitness-level model is installed. Rule-based recommendations remain available.")
    try:
        return joblib.load(MODEL_PATH)
    except Exception as exc:
        raise ModelUnavailable("The saved model could not be loaded; use rule-based recommendations instead.") from exc


def predict_fitness_level(values):
    model=_load()
    row=pd.DataFrame([values],columns=model["features"])
    prediction=float(model["pipeline"].predict(row)[0])
    return {"prediction":round(prediction,2),"target":"fitness_level","source":"machine_learning",
        "evaluation":model["evaluation"],"disclaimer":"Dataset score estimate only. The dataset does not define fitness_level units or clinical meaning; this is not a health assessment."}
