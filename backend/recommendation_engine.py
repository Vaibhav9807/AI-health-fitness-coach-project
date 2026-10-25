"""Explainable rule-based coaching recommendations."""


def recommendations(profile, workouts_this_week=0):
    goal = profile.get("goal", "general_fitness")
    exp = profile.get("experience", "beginner")
    minutes = int(profile.get("workout_minutes", 30))
    sessions = 3 if exp == "beginner" else 4
    activity_level = profile.get("activity_level", "light")
    activity_note = ("If most of your day is seated, add easy walking in small, comfortable bouts." if activity_level == "sedentary" else
                     "Build on your activity level with planned strength sessions and enough recovery." if activity_level in ("active", "very_active") else
                     "Balance your usual activity with planned strength, mobility, and rest.")
    focus = {"weight_loss": "Combine full-body strength with comfortable, low-impact cardio.",
             "weight_gain": "Prioritize progressive strength training and consistent meals.",
             "muscle_building": "Use progressive resistance training and allow muscle groups time to recover.",
             "maintain": "Balance strength, mobility, and enjoyable cardio.",
             "general_fitness": "Build a balanced routine of strength, cardio, and mobility."}.get(goal, "Build a balanced routine of strength, cardio, and mobility.")
    if workouts_this_week >= sessions:
        progress_note = f"You have logged {workouts_this_week} sessions this week and reached your current weekly target. Keep recovery part of the plan."
    elif workouts_this_week:
        progress_note = f"You have logged {workouts_this_week} session{'s' if workouts_this_week != 1 else ''} this week. Build gradually toward {sessions}; consistency matters more than rushing."
    else:
        progress_note = f"No workouts logged this week yet. A short, comfortable session is a good place to begin; your current plan suggests {sessions} sessions across the week."
    return {"source": "rule_based", "label": "Personalized rules", "daily": focus, "progress_note": progress_note, "activity_note": activity_note,
            "weekly_schedule": ["Mon · Full-body strength (" + str(minutes) + " min)", "Tue · Easy walk or mobility", "Wed · Rest or gentle movement", "Thu · " + focus, "Fri · Rest", "Sat · Cardio you enjoy (20–30 min)", "Sun · Rest and plan the week"] if sessions <= 3 else ["Mon · Strength A", "Tue · Easy cardio", "Wed · Strength B", "Thu · Rest", "Fri · Strength C", "Sat · Walk or mobility", "Sun · Rest"],
            "sessions_per_week": sessions, "intensity": "Start at a conversational pace; increase duration or load gradually.",
            "recovery": "Aim for at least one full rest day weekly; pause if you feel pain or unwell.",
            "nutrition": "Include a variety of vegetables, fruit, whole grains, and protein sources. Adjust portions to hunger and your goals.",
            "hydration": "Keep water nearby and drink regularly, especially around exercise; needs vary with heat and activity.",
            "habits": "Schedule short sessions, track how you feel, and prioritize a consistent sleep routine."}
