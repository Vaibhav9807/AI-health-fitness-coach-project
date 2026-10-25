# Dataset analysis and model

`data_analysis.py` inspects the actual supplied CSV with Pandas and reports its shape, columns, types, null counts, duplicates, categorical values, numeric summary, and invalid ranges. The reviewed dataset details and limitations are in [`../data/DATASET_REPORT.md`](../data/DATASET_REPORT.md).

`train_model.py` uses `fitness_level` as a continuous target because that is the dataset's numeric score-like field. The dataset does not define its units or scoring method, so predictions are labeled experimental dataset score estimates and must not be presented as clinical fitness status. `calories_burned` is not selected: its units are absent and its median is 13 for workout rows with a median 70-minute duration.

The model uses age, weight, daily steps, activity type, and workout duration. It excludes participant ID and date. Exact duplicate records are removed; the two negative step-count rows are excluded. It uses a participant-grouped holdout (2,400 train participants; 600 held-out participants), with 30 sampled rows per participant for local training time. Numeric imputation/scaling and categorical encoding are in a single Scikit-learn pipeline fitted only on training records.

On the held-out participants, MAE was 2.4887 score units and R² was 0.6617, versus median-baseline MAE 4.7569. This is an evaluation of predicting the supplied dataset field, not evidence of health validity or causation. The artifact is saved at `models/fitness_level.joblib` and loaded by `predict.py`; `/api/model-prediction` only provides this estimate to the signed-in user after taking age and weight from that user's own profile. The rule-based recommendation engine is separate and remains available regardless of model status.

Re-train from the project root on Windows:

```powershell
python ai/data_analysis.py
python ai/train_model.py
```

To inspect/evaluate without replacing the model file:

```powershell
python ai/train_model.py --no-save
```

The dataset may contain sensitive health information. Keep the source file, derived model, and user records private; do not publish or repurpose them without appropriate permission.
