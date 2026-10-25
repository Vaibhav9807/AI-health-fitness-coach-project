# Supplied health and fitness dataset review

Inspected with Pandas from the user-provided `health_fitness_dataset.csv` on 2026-10-15.

## Shape and quality

- 687,701 rows × 22 columns.
- 3,000 distinct participant IDs; records span 2024-01-01 through 2024-12-25.
- 0 exact duplicate rows and 0 duplicate `(participant_id, date)` keys.
- `health_condition` is missing on 490,275 rows (71.3%). It is excluded from the model.
- `daily_steps` has 2 negative values. Those records are excluded before training; all other checked profile and workout ranges are within reasonable validation bounds.
- No target or feature values were otherwise missing.

## Columns

`participant_id`, `date`, `age`, `gender`, `height_cm`, `weight_kg`, `activity_type`, `duration_minutes`, `intensity`, `calories_burned`, `avg_heart_rate`, `hours_sleep`, `stress_level`, `daily_steps`, `hydration_level`, `bmi`, `resting_heart_rate`, `blood_pressure_systolic`, `blood_pressure_diastolic`, `health_condition`, `smoking_status`, `fitness_level`.

Demographic and health information: age, gender, height, weight, BMI, health condition, smoking status, sleep, stress, hydration, heart rate, blood pressure, and steps. Workout information: date, activity, duration, intensity, and the dataset's `calories_burned` value. `participant_id` identifies repeated records and is not a model input.

## Basic numeric summary

| Column | Min | Median | Mean | Max |
|---|---:|---:|---:|---:|
| age | 18 | 42 | 41.659 | 64 |
| height_cm | 145.0 | 168.2 | 168.588 | 198.5 |
| weight_kg | 45.3 | 94.6 | 94.922 | 188.4 |
| duration_minutes | 20 | 70 | 70.012 | 120 |
| calories_burned | 0.8 | 13.0 | 15.381 | 92.0 |
| avg_heart_rate | 82 | 130 | 131.454 | 206 |
| hours_sleep | 4.0 | 7.0 | 7.049 | 10.0 |
| stress_level | 1 | 5 | 5.252 | 10 |
| daily_steps | -419 | 8,607 | 8,628.371 | 17,241 |
| hydration_level | 1.5 | 2.5 | 2.499 | 3.5 |
| bmi | 14.2 | 22.4 | 22.733 | 38.8 |
| fitness_level | 0.02 | 9.51 | 9.525 | 21.93 |

## Model decision and evaluation

`fitness_level` is the only plausible continuous score target by name. Its units and definition are absent, so this is explicitly an estimate of the dataset field, not a validated fitness or health measure. The model uses age, weight, daily steps, activity type, and workout duration. `participant_id`, date, BMI, `health_condition`, and `calories_burned` are excluded to avoid identifier leakage, target ambiguity, or relying on an inadequately defined calorie field. Feature correlations are associations and do not imply causes.

The training script excludes the two invalid negative-step records, removes exact duplicates, then samples 30 records per participant (90,000 rows) for practical local training. It holds out 600 entire participants (18,000 test rows); 2,400 participants are in training. Imputation, scaling, and categorical encoding are fit inside the training pipeline only.

| Evaluation on held-out participants | Result |
|---|---:|
| Model | HistGradientBoostingRegressor |
| Mean absolute error | 2.4887 score units |
| R² | 0.6617 |
| Median baseline MAE | 4.7569 score units |

The model beats this baseline on the grouped holdout, but score units and real-world validity are unknown. It is shown only as an experimental dataset score estimate. It is not used for BMI/BMR/TDEE, diet, diagnosis, or the rule-based coaching recommendations.

`calories_burned` has a median of 13 despite workout durations with a median of 70 minutes, and its units are not stated. It is therefore not treated as verified calories. `health_condition` is not used as a feature or displayed.
