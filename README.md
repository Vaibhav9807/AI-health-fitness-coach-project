# AI-Powered Personal Health & Fitness Coach

A local-first fitness coaching project with a responsive dashboard, Flask REST API, Flask-SQLAlchemy, SQLite, secure password hashing, workout and weight tracking, health estimates, saved meal plans, saved recommendations, and a rule-based fitness chat assistant. The supplied dataset also powers a separately evaluated, experimental `fitness_level` score model. No paid API key is needed for the core app.

## Requirements

- Windows 10/11
- Python 3.10 or newer
- A modern browser
- Internet access for the optional Google Fonts and Chart.js CDN and for Unsplash photography. Core data and APIs run locally; charts and remote photos need an internet connection.

## Install and run (PowerShell)

From the project folder:

```powershell
py -3 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

For a local classroom demo, the default development secret works. Before sharing the app beyond localhost, put a long random `SECRET_KEY` in `.env` (and set `COOKIE_SECURE=true` when using HTTPS). To enable the optional provider, set `OPENAI_API_KEY` and optionally `OPENAI_MODEL` there. The built-in server binds to `127.0.0.1`; do not expose Flask's development server to the public internet.

Initialize SQLite and start the application:

```powershell
python run.py
```

The database file `instance/fitness.db` and all tables are created on first launch. If the earlier `instance/coach.sqlite3` file exists, its accounts, password hashes, profiles, workouts, and weight records are imported into the new database without changing their IDs. The old file is left intact. Open <http://127.0.0.1:5000>. Database location can be overridden with `DATABASE_PATH`. User records persist across refreshes and account deletion cascades through that user's data.

### Run from VS Code

Open this project folder in VS Code, then choose **Terminal → New Terminal**. Run the PowerShell environment and install commands above once, then use `python run.py` whenever you want to start the local app. Keep the terminal open and visit <http://127.0.0.1:5000> in your browser. Stop the server with `Ctrl+C`.

## Features

- Register, log in, log out, and delete an account. Passwords are hashed; private routes require a session and records are scoped by user ID.
- Profile-aware BMI, Mifflin–St Jeor BMR, estimated TDEE, and goal-adjusted calorie range. Inputs are validated and incomplete information produces a request for the missing fields.
- Explainable rule-based weekly workout and recovery recommendations.
- A date-specific daily checklist with seven starter habits, custom tasks, completion counts and percentage, a progress bar, reset, and saved completion history.
- An adjustable daily water goal, quick-add intake buttons, and editable/removable dated entries. Water guidance is general tracking information, not a medical target.
- Eight editable workout templates (chest, back, shoulders, arms, legs, abs, full body, and cardio). Goal and experience shape the recommendation and set count. Exercise checkboxes are always user-controlled; plans are never checked off automatically.
- ORM-backed relational models for accounts, profiles, logged workouts, weights, saved diet plans, recommendations, daily tasks and completions, workout plans/exercises/completions, and daily water goals/entries, with per-user ownership and foreign-key cascades.
- Local sample meal planner with vegetarian/vegan selection and comma-separated allergy filtering. Nutrition values are rough examples, not clinical guidance.
- Rule-based chat fallback. If `OPENAI_API_KEY` is configured in `.env`, general fitness questions can use the server-side OpenAI Chat Completions API (`OPENAI_MODEL` selects the model); a timeout, provider error, or missing key falls back to local rules. Medical-risk questions stay on the local safe response. Only the current question is sent; profile data and API keys are never sent to the browser. No key is needed for the app to work.
- Workout history, weight check-ins, date-filtered charts, weekly frequency, and empty states based on saved records.
- Responsive layouts, readable type, loading and success/error feedback, accessible controls, and real Unsplash photos with in-app fallbacks if an image cannot load.
- Dataset-driven fitness-level score estimate, with model status shown in the workout page only when the evaluated model artifact is present. The estimate is distinct from calculated BMI/BMR/TDEE and rule-based recommendations.

## REST API

All request bodies are JSON. Authentication uses the Flask session cookie.

| Method | Route | Purpose |
|---|---|---|
| POST | `/api/register`, `/api/login`, `/api/logout` | Authentication |
| GET | `/api/me`, `/api/profile` · PUT `/api/profile` | Session and profile |
| POST | `/api/health-metrics` | Estimate BMI, BMR, TDEE, range |
| GET | `/api/recommendations`, `/api/workout-plan`, `/api/diet-plan` | Local plans |
| GET/POST | `/api/workouts` | List/add workouts |
| DELETE | `/api/workouts/<id>` | Delete own workout |
| GET/POST | `/api/progress` | Read date-filtered progress/add weight |
| GET | `/api/model-status` | Check whether the evaluated local dataset model is available |
| POST | `/api/model-prediction` | Dataset fitness-level score estimate using the signed-in user's profile |
| POST | `/api/chat` | Rule-based general fitness response |
| DELETE | `/api/account` | Confirm with password and delete account/data |
| GET/POST | `/api/daily-tasks` | Read or add tasks for a date |
| PUT | `/api/daily-tasks/<id>/completion` · POST `/api/daily-tasks/reset` | Check off a task or reset today's checklist |
| GET/PUT | `/api/water`, `/api/water/goal` | Read today's intake or set a daily goal |
| POST/PATCH/DELETE | `/api/water`, `/api/water/<id>` | Add, correct, or remove today's own intake entry |
| GET/POST | `/api/workout-plans` | Read plan templates/history or create a plan from a sample |
| POST | `/api/workout-plans/<id>/exercises` | Add an exercise to your plan |
| PATCH/DELETE | `/api/workout-exercises/<id>` | Edit or remove an exercise |
| PUT | `/api/workout-exercises/<id>/completion` | Save an exercise completion check |

New tables are `daily_tasks`, `task_completions`, `workout_plans`, `workout_exercises`, `workout_completions`, `water_goals`, and `water_intakes`. They are created alongside the existing schema with `create_all`; existing tables and user records are not dropped or recreated. The new records use foreign keys to the existing user table and are filtered by the signed-in user's ID.

## Test

```powershell
python -m unittest discover -s tests -v
```

Tests use temporary SQLite databases and cover frontend assets, authentication, validation, calculations, workout and progress persistence, task reset and completion, water-goal and intake correction, workout-plan exercise editing and completion, user isolation, allergen filtering, chat fallback, and cascading account deletion.

### Manually try the new features

1. Register or log in and open **Overview**. Check a daily task, add a personal task, and try **Reset today**.
2. Change the water goal, use a quick-add button, then edit or remove that entry in the list.
3. Open **Workouts**, choose a suggested or other sample category, check individual exercises as you finish them, and try saving, adding, or removing an exercise.
4. Register a second account in a separate browser profile to confirm its checklist, plans, and water totals are independent.

## Optional AI / ML work

The CSV you supplied is stored under `data/`. Review [the dataset report](data/DATASET_REPORT.md) for its shape, data quality, selected features and target, model evaluation, and limitations. Reinspect or retrain from the project root:

```powershell
python ai/data_analysis.py
python ai/train_model.py
```

The model targets the dataset's numeric `fitness_level` field. Because the CSV does not document that score's units or meaning, the UI labels its output as an experimental dataset estimate, not a health assessment. Training excludes `participant_id` and dates, removes exact duplicates, excludes the two negative-step rows, samples records by participant for local training time, and holds out entire participants. Preprocessing is fitted only on training data. It reports MAE/R² against a median baseline and refuses to retain a model that does not beat that baseline. To evaluate without replacing the saved artifact, run `python ai/train_model.py --no-save`. Details and privacy notes are in [ai/README.md](ai/README.md).

## Privacy and limitations

The app stores account credentials, profile, workout, weight, generated meal-plan, and recommendation records in a local SQLite database. The CSV contains sensitive health-related information; keep it private and do not repurpose or publish it without permission. Account deletion cascades to the user's records. The app is educational, not a medical device or substitute for a qualified healthcare professional. BMI is a screening measure; BMR, TDEE, meal nutrition, and the dataset score are estimates. The dataset does not define the `fitness_level` scale. The BMR equation uses sex-specific constants and may not fit every person. Recommendations are general and should be adapted to individual abilities and needs.
