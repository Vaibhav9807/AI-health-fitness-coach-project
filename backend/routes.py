"""REST API routes using authenticated SQLAlchemy records."""
import hashlib
import json
import os
import re
import secrets
import smtplib
from datetime import date, datetime, timedelta, timezone
from email.message import EmailMessage
from functools import wraps
from flask import Blueprint, current_app, jsonify, request, session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from werkzeug.security import check_password_hash, generate_password_hash
from .extensions import db
from .models import (User, UserProfile, WorkoutRecord, WeightRecord, DietPlan, Recommendation,
                     DailyTask, TaskCompletion, WorkoutPlan, WorkoutExercise,
                     WorkoutCompletion, WaterGoal, WaterIntake, PasswordResetToken)
from .calculations import health_metrics
from .recommendation_engine import recommendations
from .diet_planner import meal_plan
from .chatbot import chat_reply
from .workout_plans import WORKOUT_CATALOG, recommended_category
from ai.predict import predict_fitness_level, ModelUnavailable, MODEL_PATH

api = Blueprint("api", __name__, url_prefix="/api")
PROFILE_FIELDS = {"age", "height_cm", "weight_kg", "sex", "activity_level", "goal", "dietary_preference", "experience", "workout_minutes", "restrictions"}
ACTIVITY = {"sedentary", "light", "moderate", "active", "very_active"}
GOALS = {"weight_loss", "weight_gain", "muscle_building", "general_fitness", "maintain"}


def login_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            return jsonify(error="Please log in to continue."), 401
        if db.session.get(User, session["user_id"]) is None:
            session.clear()
            return jsonify(error="Please log in to continue."), 401
        return fn(*args, **kwargs)
    return wrapped


def body():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ValueError("Send a valid JSON object.")
    return data


def current_user():
    return db.session.get(User, session["user_id"])


def user_dict(u):
    raw_name = (u.full_name or "").strip()
    if not raw_name:
        handle = u.email.split('@')[0].split('.')[0].replace('_', ' ').replace('-', ' ').title()
        raw_name = handle or "Friend"
    return {
        "id": u.id,
        "email": u.email,
        "full_name": u.full_name or "",
        "display_name": raw_name
    }


def profile_row(user):
    p = user.profile
    return {"user_id":user.id,"age":p.age,"height_cm":p.height_cm,"weight_kg":p.weight_kg,"sex":p.sex,
            "activity_level":p.activity_level,"goal":p.goal,"dietary_preference":p.dietary_preference,
            "experience":p.experience,"workout_minutes":p.workout_minutes,"restrictions":p.restrictions}


def validate_profile(data):
    p = {k:v for k,v in data.items() if k in PROFILE_FIELDS}
    for field, lo, hi in (("age",13,100),("height_cm",100,250),("weight_kg",25,350),("workout_minutes",5,240)):
        if field not in p: continue
        if p[field] in (None, ""):
            p[field] = None
            continue
        try: n=float(p[field])
        except (ValueError,TypeError): raise ValueError(f"{field.replace('_',' ').title()} must be a number.")
        if not lo <= n <= hi: raise ValueError(f"{field.replace('_',' ').title()} must be between {lo} and {hi}.")
        p[field] = int(n) if field in ("age","workout_minutes") else n
    if "sex" in p and p["sex"] not in (None,"","female","male"): raise ValueError("Choose female or male for the BMR estimate.")
    if "sex" in p and p["sex"]=="": p["sex"]=None
    if "activity_level" in p and p["activity_level"] not in ACTIVITY: raise ValueError("Choose a valid activity level.")
    if "goal" in p and p["goal"] not in GOALS: raise ValueError("Choose a valid fitness goal.")
    if "dietary_preference" in p and p["dietary_preference"] not in {"anything","vegetarian","vegan","non_vegetarian"}: raise ValueError("Choose a valid dietary preference.")
    if "experience" in p and p["experience"] not in {"beginner","intermediate","advanced"}: raise ValueError("Choose a valid experience level.")
    if "restrictions" in p: p["restrictions"] = str(p["restrictions"])[:500]
    return p


@api.errorhandler(ValueError)
def invalid(error):
    return jsonify(error=str(error)), 400


@api.errorhandler(SQLAlchemyError)
def database_error(error):
    db.session.rollback()
    current_app.logger.exception("Database operation failed", exc_info=error)
    return jsonify(error="The database could not complete that request. Please try again."), 500


@api.post("/register")
def register():
    data = body()
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))
    confirm_password = str(data.get("confirm_password", ""))
    full_name = str(data.get("full_name", "")).strip()

    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
        raise ValueError("Enter a valid email address.")
    if len(password) < 10 or len(password) > 128:
        raise ValueError("Password must be 10–128 characters.")
    if confirm_password and confirm_password != password:
        raise ValueError("Password and confirmation password do not match.")
    if not full_name:
        full_name = email.split('@')[0].split('.')[0].replace('_', ' ').replace('-', ' ').title()
    elif len(full_name) > 120:
        raise ValueError("Full name must be 120 characters or fewer.")

    user = User(full_name=full_name, email=email, password_hash=generate_password_hash(password))
    user.profile = UserProfile()
    db.session.add(user)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify(error="An account with that email already exists."), 409
    session.clear()
    session["user_id"] = user.id
    return jsonify(user=user_dict(user), profile=profile_row(user)), 201


@api.post("/login")
def login():
    data = body()
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))
    user = User.query.filter_by(email=email).first()
    if not user or not check_password_hash(user.password_hash, password):
        return jsonify(error="Email or password is incorrect."), 401
    session.clear()
    session["user_id"] = user.id
    return jsonify(user=user_dict(user), profile=profile_row(user))


@api.post("/logout")
def logout():
    session.clear()
    return jsonify(message="Logged out.")


@api.get("/me")
@login_required
def me():
    u = current_user()
    return jsonify(user=user_dict(u), profile=profile_row(u))


@api.route("/profile", methods=["GET", "PUT"])
@login_required
def profile():
    user = current_user()
    if request.method == "PUT":
        data = body()
        if "full_name" in data:
            fn = str(data["full_name"]).strip()
            if not fn or len(fn) > 120:
                raise ValueError("Full name must be 1–120 characters.")
            user.full_name = fn
        p = validate_profile(data)
        for key, value in p.items():
            setattr(user.profile, key, value)
        if p.get("weight_kg"):
            today = date.today().isoformat()
            saved = WeightRecord.query.filter_by(user_id=user.id, record_date=today).first()
            if saved:
                saved.weight_kg = p["weight_kg"]
            else:
                db.session.add(WeightRecord(user_id=user.id, weight_kg=p["weight_kg"], record_date=today))
        db.session.commit()
    return jsonify(user=user_dict(user), profile=profile_row(user))


@api.put("/change-password")
@login_required
def change_password():
    user = current_user()
    data = body()
    current_pw = str(data.get("current_password", ""))
    new_pw = str(data.get("new_password", ""))
    confirm_pw = str(data.get("confirm_password", ""))

    if not check_password_hash(user.password_hash, current_pw):
        return jsonify(error="Current password is incorrect."), 400
    if len(new_pw) < 10 or len(new_pw) > 128:
        raise ValueError("New password must be 10–128 characters.")
    if confirm_pw and confirm_pw != new_pw:
        raise ValueError("New password and confirmation do not match.")

    user.password_hash = generate_password_hash(new_pw)
    db.session.commit()
    return jsonify(message="Password updated successfully.")


def _send_smtp_email(to_email, subject, body_text):
    host = os.getenv("SMTP_HOST")
    if not host:
        return False
    port = int(os.getenv("SMTP_PORT", 587))
    user = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASSWORD")
    from_addr = os.getenv("SMTP_FROM", user or "noreply@fitnesscoach.local")
    use_tls = os.getenv("SMTP_USE_TLS", "true").lower() == "true"

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to_email
    msg.set_content(body_text)

    try:
        server = smtplib.SMTP(host, port, timeout=10)
        if use_tls:
            server.starttls()
        if user and password:
            server.login(user, password)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as err:
        current_app.logger.warning("SMTP delivery failed: %s", err)
        return False


@api.post("/forgot-password")
def forgot_password():
    data = body()
    email = str(data.get("email", "")).strip().lower()
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
        raise ValueError("Enter a valid email address.")

    user = User.query.filter_by(email=email).first()
    dev_reset_url = None

    if user:
        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        expires_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=30)
        reset_record = PasswordResetToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at,
            used=False
        )
        db.session.add(reset_record)
        db.session.commit()

        reset_url = f"{request.host_url.rstrip('/')}/?reset_token={raw_token}"
        subject = "Reset your AI Health & Fitness Coach password"
        message_body = (
            f"Hello {user.full_name or 'there'},\n\n"
            f"A password reset was requested for your account ({user.email}).\n"
            f"Open the link below (valid for 30 minutes) to choose a new password:\n\n"
            f"{reset_url}\n\n"
            f"If you did not request this, you can safely ignore this message.\n"
        )
        sent = _send_smtp_email(user.email, subject, message_body)
        is_dev = os.getenv("FLASK_DEBUG", "false").lower() == "true" or not os.getenv("SMTP_HOST")
        if is_dev or not sent:
            current_app.logger.info("[DEV] Password reset link for %s: %s", user.email, reset_url)
            dev_reset_url = reset_url

    return jsonify(
        message="If that email is registered, password reset instructions have been sent.",
        dev_reset_url=dev_reset_url
    )


@api.get("/verify-reset-token")
def verify_reset_token():
    token = request.args.get("token", "").strip()
    if not token:
        return jsonify(valid=False, error="Reset token is missing."), 400
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    record = PasswordResetToken.query.filter_by(token_hash=token_hash, used=False).first()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if not record or record.expires_at < now:
        return jsonify(valid=False, error="This reset link is invalid or has expired.")
    return jsonify(valid=True, email=record.user.email)


@api.post("/reset-password")
def reset_password():
    data = body()
    token = str(data.get("token", "")).strip()
    password = str(data.get("password", ""))
    confirm_password = str(data.get("confirm_password", ""))

    if not token:
        raise ValueError("Reset token is required.")
    if len(password) < 10 or len(password) > 128:
        raise ValueError("Password must be 10–128 characters.")
    if confirm_password and confirm_password != password:
        raise ValueError("Password and confirmation password do not match.")

    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    record = PasswordResetToken.query.filter_by(token_hash=token_hash, used=False).first()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if not record or record.expires_at < now:
        return jsonify(error="Reset link is invalid or has expired. Please request a new one."), 400

    user = record.user
    user.password_hash = generate_password_hash(password)
    record.used = True
    PasswordResetToken.query.filter(
        PasswordResetToken.user_id == user.id,
        PasswordResetToken.id != record.id
    ).update({"used": True})
    db.session.commit()
    session.clear()
    return jsonify(message="Password reset successfully. Please log in with your new password.")


@api.post("/health-metrics")
@login_required
def metrics():
    p=profile_row(current_user()); data=body(); p.update({k:v for k,v in data.items() if k in PROFILE_FIELDS})
    try:return jsonify(metrics=health_metrics(p))
    except ValueError as e:return jsonify(error=str(e)),400


def user_recommendations(user):
    today=date.today(); monday=today.fromordinal(today.toordinal()-today.weekday()).isoformat()
    count=WorkoutRecord.query.filter(WorkoutRecord.user_id==user.id,WorkoutRecord.exercise_date.between(monday,today.isoformat())).count()
    result=recommendations(profile_row(user),count)
    db.session.add(Recommendation(user_id=user.id,recommendation_type="workout",content_json=json.dumps(result)))
    db.session.commit()
    return result


@api.get("/recommendations")
@login_required
def recs(): return jsonify(recommendations=user_recommendations(current_user()))


@api.get("/workout-plan")
@login_required
def plan(): return jsonify(plan=user_recommendations(current_user()))


@api.get("/diet-plan")
@login_required
def diet():
    user=current_user(); p=profile_row(user); result=meal_plan(p)
    try: result["calorie_range"]=health_metrics(p)["calorie_range"]
    except ValueError: result["calorie_range"]=None
    db.session.add(DietPlan(user_id=user.id,plan_json=json.dumps(result))); db.session.commit()
    return jsonify(plan=result)


@api.get("/model-status")
@login_required
def model_status():
    return jsonify(available=MODEL_PATH.is_file(),target="fitness_level",note="Dataset score only; the source CSV does not define the target's units or clinical meaning.")


@api.post("/model-prediction")
@login_required
def model_prediction():
    data=body(); profile=profile_row(current_user())
    if not profile.get("age") or not profile.get("weight_kg"):
        raise ValueError("Add your age and current weight to your profile before requesting this dataset estimate.")
    activity=str(data.get("activity_type", ""))
    if activity not in {"Yoga","Weight Training","HIIT","Dancing","Cycling","Basketball","Tennis","Walking","Swimming","Running"}:
        raise ValueError("Choose an activity represented in the dataset.")
    try: duration=int(data.get("duration_minutes")); steps=int(data.get("daily_steps"))
    except (ValueError,TypeError): raise ValueError("Enter a valid duration and daily step count.")
    if not 1<=duration<=600: raise ValueError("Duration must be between 1 and 600 minutes.")
    if not 0<=steps<=100000: raise ValueError("Daily steps must be between 0 and 100,000.")
    features={"age":profile["age"],"weight_kg":profile["weight_kg"],"daily_steps":steps,"activity_type":activity,"duration_minutes":duration}
    try: return jsonify(result=predict_fitness_level(features))
    except ModelUnavailable as error: return jsonify(error=str(error)),503


@api.route("/workouts", methods=["GET","POST"])
@login_required
def workouts():
    uid=session["user_id"]
    if request.method=="POST":
        d=body(); exercise=str(d.get("exercise_type","")).strip(); notes=str(d.get("notes", ""))[:500]
        try: minutes=int(d.get("duration_minutes")); day=date.fromisoformat(d.get("exercise_date",date.today().isoformat())).isoformat()
        except (ValueError,TypeError): raise ValueError("Enter a valid duration and exercise date.")
        if day>date.today().isoformat(): raise ValueError("Exercise date cannot be in the future.")
        if not exercise or len(exercise)>60: raise ValueError("Exercise type must be 1–60 characters.")
        if not 1<=minutes<=600: raise ValueError("Duration must be between 1 and 600 minutes.")
        record=WorkoutRecord(user_id=uid,exercise_type=exercise,duration_minutes=minutes,exercise_date=day,notes=notes)
        db.session.add(record); db.session.commit()
        return jsonify(workout={"id":record.id,"user_id":uid,"exercise_type":exercise,"duration_minutes":minutes,"exercise_date":day,"notes":notes}),201
    rows=WorkoutRecord.query.filter_by(user_id=uid).order_by(WorkoutRecord.exercise_date.desc(),WorkoutRecord.id.desc()).limit(200).all()
    return jsonify(workouts=[{"id":r.id,"user_id":r.user_id,"exercise_type":r.exercise_type,"duration_minutes":r.duration_minutes,"exercise_date":r.exercise_date,"notes":r.notes,"created_at":r.created_at.isoformat()} for r in rows])


@api.delete("/workouts/<int:record_id>")
@login_required
def delete_workout(record_id):
    record=WorkoutRecord.query.filter_by(id=record_id,user_id=session["user_id"]).first()
    if not record:return jsonify(error="Workout not found."),404
    db.session.delete(record);db.session.commit()
    return jsonify(message="Workout deleted.")


@api.put("/workouts/<int:record_id>")
@login_required
def update_workout(record_id):
    record = WorkoutRecord.query.filter_by(id=record_id, user_id=session["user_id"]).first()
    if not record:
        return jsonify(error="Workout not found."), 404
    d = body()
    exercise = str(d.get("exercise_type", record.exercise_type)).strip()
    notes = str(d.get("notes", record.notes))[:500]
    try:
        minutes = int(d.get("duration_minutes", record.duration_minutes))
        day = date.fromisoformat(d.get("exercise_date", record.exercise_date)).isoformat()
    except (ValueError, TypeError):
        raise ValueError("Enter a valid duration and exercise date.")
    if day > date.today().isoformat():
        raise ValueError("Exercise date cannot be in the future.")
    if not exercise or len(exercise) > 60:
        raise ValueError("Exercise type must be 1–60 characters.")
    if not 1 <= minutes <= 600:
        raise ValueError("Duration must be between 1 and 600 minutes.")
    record.exercise_type = exercise
    record.duration_minutes = minutes
    record.exercise_date = day
    record.notes = notes
    db.session.commit()
    return jsonify(workout={
        "id": record.id,
        "user_id": record.user_id,
        "exercise_type": record.exercise_type,
        "duration_minutes": record.duration_minutes,
        "exercise_date": record.exercise_date,
        "notes": record.notes
    })


@api.route("/progress",methods=["GET","POST"])
@login_required
def progress():
    uid=session["user_id"]
    if request.method=="POST":
        d=body()
        try: weight=float(d.get("weight_kg")); day=date.fromisoformat(d.get("record_date",date.today().isoformat())).isoformat()
        except (ValueError,TypeError):raise ValueError("Enter a valid weight and date.")
        if not 25<=weight<=350:raise ValueError("Weight must be between 25 and 350 kg.")
        row=WeightRecord.query.filter_by(user_id=uid,record_date=day).first()
        if row:row.weight_kg=weight
        else:db.session.add(WeightRecord(user_id=uid,weight_kg=weight,record_date=day))
        db.session.commit()
    start=request.args.get("start","0001-01-01"); end=request.args.get("end","9999-12-31")
    try: date.fromisoformat(start); date.fromisoformat(end)
    except ValueError:raise ValueError("Date filter must use YYYY-MM-DD.")
    weights=WeightRecord.query.filter(WeightRecord.user_id==uid,WeightRecord.record_date.between(start,end)).order_by(WeightRecord.record_date).all()
    workouts=WorkoutRecord.query.filter(WorkoutRecord.user_id==uid,WorkoutRecord.exercise_date.between(start,end)).order_by(WorkoutRecord.exercise_date).all()
    today=date.today(); week_start=today.fromordinal(today.toordinal()-today.weekday()).isoformat()
    week=db.session.query(WorkoutRecord.exercise_date,db.func.count(WorkoutRecord.id)).filter(WorkoutRecord.user_id==uid,WorkoutRecord.exercise_date.between(week_start,today.isoformat())).group_by(WorkoutRecord.exercise_date).order_by(WorkoutRecord.exercise_date).all()
    return jsonify(weights=[{"weight_kg":r.weight_kg,"record_date":r.record_date} for r in weights],workouts=[{"exercise_type":r.exercise_type,"duration_minutes":r.duration_minutes,"exercise_date":r.exercise_date} for r in workouts],weekly=[{"exercise_date":d,"count":n} for d,n in week],workouts_this_week=sum(n for _d,n in week))


@api.post("/chat")
@login_required
def chat():
    message=str(body().get("message", "")).strip()
    if not message or len(message)>1000:raise ValueError("Enter a message of 1–1000 characters.")
    return jsonify(chat_reply(message))


@api.delete("/account")
@login_required
def delete_account():
    d=body(); user=current_user()
    if not d.get("confirmation") or not check_password_hash(user.password_hash,str(d.get("password", ""))):return jsonify(error="Enter your password and confirm account deletion."),400
    db.session.delete(user);db.session.commit();session.clear()
    return jsonify(message="Account and associated records deleted.")


DAILY_TASK_DEFAULTS = (
    "Drink enough water", "Eat a healthy breakfast", "Eat fruits and vegetables",
    "Walk for 30 minutes", "Complete daily exercise", "Follow the meal plan",
    "Sleep for 7–9 hours",
)


def parse_local_day(value, *, default=None):
    if value in (None, ""):
        return default or date.today()
    try:
        day = date.fromisoformat(str(value))
    except ValueError:
        raise ValueError("Date must use YYYY-MM-DD.")
    if day > date.today():
        raise ValueError("Date cannot be in the future.")
    return day


def ensure_daily_tasks(user_id, day):
    existing = {row.title for row in DailyTask.query.filter_by(user_id=user_id, task_date=day).all()}
    for title in DAILY_TASK_DEFAULTS:
        if title not in existing:
            db.session.add(DailyTask(user_id=user_id, task_date=day, title=title, is_custom=False))
    db.session.flush()


def serialize_daily_tasks(user_id, day):
    ensure_daily_tasks(user_id, day)
    tasks = DailyTask.query.filter_by(user_id=user_id, task_date=day, is_archived=False).order_by(DailyTask.id).all()
    completions = TaskCompletion.query.filter_by(user_id=user_id, completion_date=day).all()
    completed_by_task = {row.task_id: row for row in completions}
    completed_count = sum(bool(completed_by_task.get(task.id) and completed_by_task[task.id].completed) for task in tasks)
    total = len(tasks)
    return {
        "date": day.isoformat(),
        "tasks": [{"id": task.id, "title": task.title, "is_custom": task.is_custom,
                   "completed": bool(completed_by_task.get(task.id) and completed_by_task[task.id].completed)}
                  for task in tasks],
        "completed_count": completed_count,
        "total_count": total,
        "percentage": round(completed_count * 100 / total) if total else 0,
        "summary": f"All {total} tasks complete — nice work." if total and completed_count == total
                   else f"{completed_count} of {total} tasks complete. Keep going at your own pace.",
    }


@api.get("/daily-tasks")
@login_required
def daily_tasks():
    day = parse_local_day(request.args.get("date"))
    result = serialize_daily_tasks(session["user_id"], day)
    db.session.commit()
    return jsonify(result)


@api.post("/daily-tasks")
@login_required
def add_daily_task():
    data = body()
    title = str(data.get("title", "")).strip()
    if not title or len(title) > 120:
        raise ValueError("A task name must contain 1–120 characters.")
    day = parse_local_day(data.get("date"))
    uid = session["user_id"]
    duplicate = DailyTask.query.filter(DailyTask.user_id == uid, DailyTask.task_date == day,
                                       db.func.lower(DailyTask.title) == title.casefold()).first()
    if duplicate:
        return jsonify(error="That task is already on this day's list."), 409
    task = DailyTask(user_id=uid, task_date=day, title=title, is_custom=True)
    db.session.add(task)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify(error="That task is already on this day's list."), 409
    return jsonify(task={"id": task.id, "title": task.title, "is_custom": True, "completed": False}), 201


@api.put("/daily-tasks/<int:task_id>/completion")
@login_required
def complete_daily_task(task_id):
    uid = session["user_id"]
    task = DailyTask.query.filter_by(id=task_id, user_id=uid).first()
    if not task:
        return jsonify(error="Task not found."), 404
    value = body().get("completed")
    if not isinstance(value, bool):
        raise ValueError("Completion must be true or false.")
    entry = TaskCompletion.query.filter_by(task_id=task.id, user_id=uid, completion_date=task.task_date).first()
    if not entry:
        entry = TaskCompletion(task_id=task.id, user_id=uid, completion_date=task.task_date)
        db.session.add(entry)
    entry.completed = value
    entry.completed_at = datetime.now(timezone.utc) if value else None
    db.session.commit()
    return jsonify(serialize_daily_tasks(uid, task.task_date))


@api.post("/daily-tasks/reset")
@login_required
def reset_daily_tasks():
    uid = session["user_id"]
    day = date.today()
    rows = TaskCompletion.query.filter_by(user_id=uid, completion_date=day).all()
    for row in rows:
        row.completed = False
        row.completed_at = None
    db.session.commit()
    return jsonify(serialize_daily_tasks(uid, day))


@api.delete("/daily-tasks/<int:task_id>")
@login_required
def delete_daily_task(task_id):
    task = DailyTask.query.filter_by(id=task_id, user_id=session["user_id"], is_custom=True, is_archived=False).first()
    if not task:
        return jsonify(error="Custom task not found."), 404
    task.is_archived = True
    db.session.commit()
    return jsonify(message="Task removed.")


def water_snapshot(user_id, day):
    goal = WaterGoal.query.filter_by(user_id=user_id, goal_date=day).first()
    if not goal:
        goal = WaterGoal(user_id=user_id, goal_date=day, goal_ml=2000)
        db.session.add(goal)
        db.session.flush()
    entries = WaterIntake.query.filter_by(user_id=user_id, intake_date=day).order_by(WaterIntake.created_at.desc(), WaterIntake.id.desc()).all()
    total = sum(entry.amount_ml for entry in entries)
    week_start = day.fromordinal(day.toordinal() - day.weekday())
    week_rows = db.session.query(WaterIntake.intake_date, db.func.sum(WaterIntake.amount_ml)).filter(
        WaterIntake.user_id == user_id, WaterIntake.intake_date.between(week_start, day)
    ).group_by(WaterIntake.intake_date).all()
    weekly = {d.isoformat(): amount for d, amount in week_rows}
    return {"date": day.isoformat(), "goal_ml": goal.goal_ml, "intake_ml": total,
            "percentage": min(100, round(total * 100 / goal.goal_ml)) if goal.goal_ml else 0,
            "entries": [{"id": entry.id, "amount_ml": entry.amount_ml, "created_at": entry.created_at.isoformat()} for entry in entries],
            "weekly": [{"date": (week_start.fromordinal(week_start.toordinal() + offset)).isoformat(),
                        "intake_ml": weekly.get((week_start.fromordinal(week_start.toordinal() + offset)).isoformat(), 0)} for offset in range(7)]}


def parse_whole_number(raw, label):
    if isinstance(raw, bool):
        raise ValueError(f"{label} must be a whole number.")
    try:
        value = int(raw)
    except (ValueError, TypeError):
        raise ValueError(f"{label} must be a whole number.")
    if isinstance(raw, float) and raw != value:
        raise ValueError(f"{label} must be a whole number.")
    if isinstance(raw, str) and raw.strip() not in (str(value), f"+{value}"):
        raise ValueError(f"{label} must be a whole number.")
    return value


@api.get("/water")
@login_required
def get_water():
    result = water_snapshot(session["user_id"], date.today())
    db.session.commit()
    return jsonify(result)


@api.put("/water/goal")
@login_required
def set_water_goal():
    data = body()
    goal_ml = parse_whole_number(data.get("goal_ml"), "Daily water goal")
    if not 250 <= goal_ml <= 10000:
        raise ValueError("Daily water goal must be between 250 and 10,000 ml.")
    uid, day = session["user_id"], date.today()
    goal = WaterGoal.query.filter_by(user_id=uid, goal_date=day).first()
    if goal:
        goal.goal_ml = goal_ml
    else:
        db.session.add(WaterGoal(user_id=uid, goal_date=day, goal_ml=goal_ml))
    db.session.commit()
    return jsonify(water=water_snapshot(uid, day))


@api.post("/water")
@login_required
def add_water_intake():
    amount_ml = parse_whole_number(body().get("amount_ml"), "Water amount")
    if not 50 <= amount_ml <= 3000:
        raise ValueError("A single water entry must be between 50 and 3,000 ml.")
    db.session.add(WaterIntake(user_id=session["user_id"], intake_date=date.today(), amount_ml=amount_ml))
    db.session.commit()
    return jsonify(water=water_snapshot(session["user_id"], date.today())), 201


@api.patch("/water/<int:entry_id>")
@login_required
def edit_water_intake(entry_id):
    entry = WaterIntake.query.filter_by(id=entry_id, user_id=session["user_id"], intake_date=date.today()).first()
    if not entry:
        return jsonify(error="Today's water entry was not found."), 404
    amount_ml = parse_whole_number(body().get("amount_ml"), "Water amount")
    if not 50 <= amount_ml <= 3000:
        raise ValueError("A single water entry must be between 50 and 3,000 ml.")
    entry.amount_ml = amount_ml
    db.session.commit()
    return jsonify(water=water_snapshot(session["user_id"], date.today()))


@api.delete("/water/<int:entry_id>")
@login_required
def delete_water_intake(entry_id):
    entry = WaterIntake.query.filter_by(id=entry_id, user_id=session["user_id"], intake_date=date.today()).first()
    if not entry:
        return jsonify(error="Today's water entry was not found."), 404
    db.session.delete(entry)
    db.session.commit()
    return jsonify(water=water_snapshot(session["user_id"], date.today()))


def validate_exercise_values(data, *, current=None):
    values = {}
    current = current or {}
    name = str(data.get("exercise_name", current.get("exercise_name", ""))).strip()
    if not name or len(name) > 120:
        raise ValueError("Exercise name must contain 1–120 characters.")
    values["exercise_name"] = name
    for field, default, low, high in (("sets", 3, 1, 10), ("repetitions", 10, 1, 100),
                                     ("duration_minutes", 0, 0, 180), ("rest_seconds", 60, 0, 600)):
        raw = data.get(field, current.get(field, default))
        if isinstance(raw, bool):
            raise ValueError(f"{field.replace('_', ' ').title()} must be a whole number.")
        try:
            value = int(raw)
        except (ValueError, TypeError):
            raise ValueError(f"{field.replace('_', ' ').title()} must be a whole number.")
        if str(raw).strip() not in (str(value), f"+{value}") or not low <= value <= high:
            raise ValueError(f"{field.replace('_', ' ').title()} must be between {low} and {high}.")
        values[field] = value
    return values


def serialize_workout_plan(plan, user_id):
    exercise_ids = [exercise.id for exercise in plan.exercises]
    checks = WorkoutCompletion.query.filter(WorkoutCompletion.user_id == user_id,
        WorkoutCompletion.completion_date == plan.plan_date,
        WorkoutCompletion.exercise_id.in_(exercise_ids)).all() if exercise_ids else []
    completed_ids = {row.exercise_id for row in checks if row.completed}
    exercises = [{"id": exercise.id, "exercise_name": exercise.exercise_name, "sets": exercise.sets,
                  "repetitions": exercise.repetitions, "duration_minutes": exercise.duration_minutes,
                  "rest_seconds": exercise.rest_seconds, "position": exercise.position,
                  "completed": exercise.id in completed_ids}
                 for exercise in plan.exercises]
    completed = len(completed_ids)
    total = len(exercises)
    estimated = round(sum(e.duration_minutes + (e.sets * e.repetitions * 3 / 60) +
                          (max(e.sets - 1, 0) * e.rest_seconds / 60) for e in plan.exercises))
    return {"id": plan.id, "name": plan.name, "focus": plan.focus, "date": plan.plan_date.isoformat(),
            "exercises": exercises, "completed_count": completed, "remaining_count": total - completed,
            "total_count": total, "percentage": round(completed * 100 / total) if total else 0,
            "estimated_minutes": estimated}


@api.get("/workout-plans")
@login_required
def get_workout_plans():
    uid = session["user_id"]
    profile = profile_row(current_user())
    recommended, reason = recommended_category(profile)
    plans = WorkoutPlan.query.filter_by(user_id=uid).order_by(WorkoutPlan.plan_date.desc(), WorkoutPlan.id.desc()).limit(100).all()
    return jsonify(recommended_category=recommended, recommendation_reason=reason,
        categories=[{"name": name, "summary": spec["summary"]} for name, spec in WORKOUT_CATALOG.items()],
        plans=[serialize_workout_plan(plan, uid) for plan in plans])


@api.post("/workout-plans")
@login_required
def create_workout_plan():
    category = str(body().get("category", "")).strip()
    if category not in WORKOUT_CATALOG:
        raise ValueError("Choose one of the sample workout categories.")
    uid = session["user_id"]
    experience = profile_row(current_user()).get("experience") or "beginner"
    sets = {"beginner": 2, "intermediate": 3, "advanced": 4}.get(experience, 2)
    spec = WORKOUT_CATALOG[category]
    plan = WorkoutPlan(user_id=uid, plan_date=date.today(), name=category, focus=category.lower())
    db.session.add(plan)
    db.session.flush()
    cardio_minutes = {"beginner": 20, "intermediate": 30, "advanced": 40}.get(experience, 20)
    cardio_shares = (0.6, 0.25, 0.15)
    for position, (exercise_name, reps) in enumerate(spec["exercises"]):
        cardio = category == "Cardio"
        db.session.add(WorkoutExercise(plan_id=plan.id, user_id=uid, exercise_name=exercise_name,
            sets=1 if cardio else sets, repetitions=1 if cardio else reps,
            duration_minutes=max(1, round(cardio_minutes * cardio_shares[position])) if cardio else 0,
            rest_seconds=0 if cardio else 60, position=position))
    db.session.commit()
    return jsonify(plan=serialize_workout_plan(plan, uid)), 201


@api.post("/workout-plans/<int:plan_id>/exercises")
@login_required
def add_workout_exercise(plan_id):
    uid = session["user_id"]
    plan = WorkoutPlan.query.filter_by(id=plan_id, user_id=uid).first()
    if not plan:
        return jsonify(error="Workout plan not found."), 404
    data = body()
    values = validate_exercise_values(data)
    values.update(plan_id=plan.id, user_id=uid, position=len(plan.exercises))
    exercise = WorkoutExercise(**values)
    db.session.add(exercise)
    db.session.commit()
    return jsonify(plan=serialize_workout_plan(plan, uid)), 201


@api.patch("/workout-exercises/<int:exercise_id>")
@login_required
def edit_workout_exercise(exercise_id):
    uid = session["user_id"]
    exercise = WorkoutExercise.query.filter_by(id=exercise_id, user_id=uid).first()
    if not exercise:
        return jsonify(error="Exercise not found."), 404
    values = validate_exercise_values(body(), current={"exercise_name": exercise.exercise_name,
        "sets": exercise.sets, "repetitions": exercise.repetitions,
        "duration_minutes": exercise.duration_minutes, "rest_seconds": exercise.rest_seconds})
    for key, value in values.items():
        setattr(exercise, key, value)
    db.session.commit()
    return jsonify(plan=serialize_workout_plan(exercise.plan, uid))


@api.delete("/workout-exercises/<int:exercise_id>")
@login_required
def delete_workout_exercise(exercise_id):
    uid = session["user_id"]
    exercise = WorkoutExercise.query.filter_by(id=exercise_id, user_id=uid).first()
    if not exercise:
        return jsonify(error="Exercise not found."), 404
    plan = exercise.plan
    db.session.delete(exercise)
    db.session.commit()
    return jsonify(plan=serialize_workout_plan(plan, uid))


@api.delete("/workout-plans/<int:plan_id>")
@login_required
def delete_workout_plan(plan_id):
    plan = WorkoutPlan.query.filter_by(id=plan_id, user_id=session["user_id"]).first()
    if not plan:
        return jsonify(error="Workout plan not found."), 404
    db.session.delete(plan)
    db.session.commit()
    return jsonify(message="Workout plan deleted.")


@api.put("/workout-exercises/<int:exercise_id>/completion")
@login_required
def complete_workout_exercise(exercise_id):
    uid = session["user_id"]
    exercise = WorkoutExercise.query.filter_by(id=exercise_id, user_id=uid).first()
    if not exercise:
        return jsonify(error="Exercise not found."), 404
    value = body().get("completed")
    if not isinstance(value, bool):
        raise ValueError("Completion must be true or false.")
    day = exercise.plan.plan_date
    entry = WorkoutCompletion.query.filter_by(exercise_id=exercise.id, user_id=uid, completion_date=day).first()
    if not entry:
        entry = WorkoutCompletion(exercise_id=exercise.id, user_id=uid, completion_date=day)
        db.session.add(entry)
    entry.completed = value
    entry.completed_at = datetime.now(timezone.utc) if value else None
    db.session.commit()
    return jsonify(plan=serialize_workout_plan(exercise.plan, uid))
