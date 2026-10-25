"""Relational models for private user fitness data and saved plans."""
from datetime import date, datetime, timezone
from sqlalchemy import UniqueConstraint
from .extensions import db


class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=True)
    email = db.Column(db.String(255), nullable=False, unique=True, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    profile = db.relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan", passive_deletes=True)
    workouts = db.relationship("WorkoutRecord", back_populates="user", cascade="all, delete-orphan", passive_deletes=True)
    weights = db.relationship("WeightRecord", back_populates="user", cascade="all, delete-orphan", passive_deletes=True)
    diet_plans = db.relationship("DietPlan", back_populates="user", cascade="all, delete-orphan", passive_deletes=True)
    recommendations = db.relationship("Recommendation", back_populates="user", cascade="all, delete-orphan", passive_deletes=True)
    daily_tasks = db.relationship("DailyTask", back_populates="user", cascade="all, delete-orphan", passive_deletes=True)
    task_completions = db.relationship("TaskCompletion", back_populates="user", cascade="all, delete-orphan", passive_deletes=True)
    workout_plans = db.relationship("WorkoutPlan", back_populates="user", cascade="all, delete-orphan", passive_deletes=True)
    workout_exercises = db.relationship("WorkoutExercise", back_populates="user", cascade="all, delete-orphan", passive_deletes=True)
    workout_completions = db.relationship("WorkoutCompletion", back_populates="user", cascade="all, delete-orphan", passive_deletes=True)
    water_goals = db.relationship("WaterGoal", back_populates="user", cascade="all, delete-orphan", passive_deletes=True)
    water_intakes = db.relationship("WaterIntake", back_populates="user", cascade="all, delete-orphan", passive_deletes=True)
    reset_tokens = db.relationship("PasswordResetToken", back_populates="user", cascade="all, delete-orphan", passive_deletes=True)


class UserProfile(db.Model):
    __tablename__ = "user_profiles"
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    age = db.Column(db.Integer)
    height_cm = db.Column(db.Float)
    weight_kg = db.Column(db.Float)
    sex = db.Column(db.String(16))
    activity_level = db.Column(db.String(24), nullable=False, default="light")
    goal = db.Column(db.String(32), nullable=False, default="general_fitness")
    dietary_preference = db.Column(db.String(24), nullable=False, default="anything")
    experience = db.Column(db.String(24), nullable=False, default="beginner")
    workout_minutes = db.Column(db.Integer, nullable=False, default=30)
    restrictions = db.Column(db.String(500), nullable=False, default="")
    user = db.relationship("User", back_populates="profile")


class WorkoutRecord(db.Model):
    __tablename__ = "workout_records"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    exercise_type = db.Column(db.String(60), nullable=False)
    duration_minutes = db.Column(db.Integer, nullable=False)
    exercise_date = db.Column(db.String(10), nullable=False, index=True)
    notes = db.Column(db.String(500), nullable=False, default="")
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    user = db.relationship("User", back_populates="workouts")


class WeightRecord(db.Model):
    __tablename__ = "weight_records"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    weight_kg = db.Column(db.Float, nullable=False)
    record_date = db.Column(db.String(10), nullable=False, index=True)
    __table_args__ = (db.UniqueConstraint("user_id", "record_date", name="uq_weight_user_date"),)
    user = db.relationship("User", back_populates="weights")


class DietPlan(db.Model):
    __tablename__ = "diet_plans"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    plan_json = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    user = db.relationship("User", back_populates="diet_plans")


class Recommendation(db.Model):
    __tablename__ = "recommendations"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    recommendation_type = db.Column(db.String(40), nullable=False, default="workout")
    content_json = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    user = db.relationship("User", back_populates="recommendations")


class DailyTask(db.Model):
    """A user's task for one local calendar day; rows preserve daily history."""
    __tablename__ = "daily_tasks"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    task_date = db.Column(db.Date, nullable=False, default=date.today, index=True)
    title = db.Column(db.String(120), nullable=False)
    is_custom = db.Column(db.Boolean, nullable=False, default=False)
    is_archived = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    __table_args__ = (UniqueConstraint("user_id", "task_date", "title", name="uq_daily_task_user_day_title"),)
    user = db.relationship("User", back_populates="daily_tasks")
    completions = db.relationship("TaskCompletion", back_populates="task", cascade="all, delete-orphan", passive_deletes=True)


class TaskCompletion(db.Model):
    __tablename__ = "task_completions"
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey("daily_tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    completion_date = db.Column(db.Date, nullable=False, default=date.today, index=True)
    completed = db.Column(db.Boolean, nullable=False, default=False)
    completed_at = db.Column(db.DateTime)
    __table_args__ = (UniqueConstraint("task_id", "completion_date", name="uq_task_completion_day"),)
    task = db.relationship("DailyTask", back_populates="completions")
    user = db.relationship("User", back_populates="task_completions")


class WorkoutPlan(db.Model):
    __tablename__ = "workout_plans"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    plan_date = db.Column(db.Date, nullable=False, default=date.today, index=True)
    name = db.Column(db.String(100), nullable=False)
    focus = db.Column(db.String(40), nullable=False, default="general_fitness")
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    user = db.relationship("User", back_populates="workout_plans")
    exercises = db.relationship("WorkoutExercise", back_populates="plan", cascade="all, delete-orphan", passive_deletes=True, order_by="WorkoutExercise.position")


class WorkoutExercise(db.Model):
    __tablename__ = "workout_exercises"
    id = db.Column(db.Integer, primary_key=True)
    plan_id = db.Column(db.Integer, db.ForeignKey("workout_plans.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    exercise_name = db.Column(db.String(120), nullable=False)
    sets = db.Column(db.Integer, nullable=False, default=3)
    repetitions = db.Column(db.Integer, nullable=False, default=10)
    duration_minutes = db.Column(db.Integer, nullable=False, default=0)
    rest_seconds = db.Column(db.Integer, nullable=False, default=60)
    position = db.Column(db.Integer, nullable=False, default=0)
    plan = db.relationship("WorkoutPlan", back_populates="exercises")
    user = db.relationship("User", back_populates="workout_exercises")
    completions = db.relationship("WorkoutCompletion", back_populates="exercise", cascade="all, delete-orphan", passive_deletes=True)


class WorkoutCompletion(db.Model):
    __tablename__ = "workout_completions"
    id = db.Column(db.Integer, primary_key=True)
    exercise_id = db.Column(db.Integer, db.ForeignKey("workout_exercises.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    completion_date = db.Column(db.Date, nullable=False, default=date.today, index=True)
    completed = db.Column(db.Boolean, nullable=False, default=False)
    completed_at = db.Column(db.DateTime)
    updated_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    __table_args__ = (UniqueConstraint("exercise_id", "completion_date", name="uq_workout_completion_day"),)
    exercise = db.relationship("WorkoutExercise", back_populates="completions")
    user = db.relationship("User", back_populates="workout_completions")


class WaterGoal(db.Model):
    __tablename__ = "water_goals"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    goal_date = db.Column(db.Date, nullable=False, default=date.today, index=True)
    goal_ml = db.Column(db.Integer, nullable=False, default=2000)
    __table_args__ = (UniqueConstraint("user_id", "goal_date", name="uq_water_goal_user_day"),)
    user = db.relationship("User", back_populates="water_goals")


class WaterIntake(db.Model):
    __tablename__ = "water_intakes"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    intake_date = db.Column(db.Date, nullable=False, default=date.today, index=True)
    amount_ml = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    user = db.relationship("User", back_populates="water_intakes")


class PasswordResetToken(db.Model):
    __tablename__ = "password_reset_tokens"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash = db.Column(db.String(128), nullable=False, unique=True, index=True)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    user = db.relationship("User", back_populates="reset_tokens")
