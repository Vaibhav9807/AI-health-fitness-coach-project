"""Sample workout plans and small helpers for personalized, editable routines."""

WORKOUT_CATALOG = {
    "Chest": {
        "summary": "A balanced push session with simple movement options.",
        "exercises": [("Incline push-up", 10), ("Dumbbell chest press", 10), ("Dumbbell floor fly", 12)],
    },
    "Back": {
        "summary": "Build a steady pull routine with supported movements.",
        "exercises": [("Resistance-band row", 12), ("Dumbbell row", 10), ("Bird dog", 10)],
    },
    "Shoulders": {
        "summary": "Shoulder-friendly presses and controlled raises.",
        "exercises": [("Seated shoulder press", 10), ("Lateral raise", 12), ("Wall slide", 10)],
    },
    "Arms": {
        "summary": "A short session for biceps, triceps, and grip.",
        "exercises": [("Dumbbell curl", 12), ("Overhead triceps extension", 10), ("Incline push-up", 10)],
    },
    "Legs": {
        "summary": "A practical lower-body session with bodyweight options.",
        "exercises": [("Chair squat", 10), ("Glute bridge", 12), ("Reverse lunge", 8)],
    },
    "Abs": {
        "summary": "A short core session focused on controlled movement.",
        "exercises": [("Dead bug", 10), ("Bird dog", 10), ("Knee plank", 1)],
    },
    "Full body": {
        "summary": "An approachable routine that covers the main movement patterns.",
        "exercises": [("Chair squat", 10), ("Incline push-up", 10), ("Resistance-band row", 12), ("Dead bug", 10)],
    },
    "Cardio": {
        "summary": "Choose a comfortable pace and build time gradually.",
        "exercises": [("Brisk walk", 1), ("Easy cycling", 1), ("Gentle cooldown", 1)],
    },
}


def recommended_category(profile):
    goal = profile.get("goal")
    experience = profile.get("experience", "beginner")
    if goal == "weight_loss":
        return "Cardio", "A steady cardio session can be a flexible starting point for your current goal."
    if goal in {"muscle_building", "weight_gain"}:
        return "Full body", "A balanced strength session is a practical place to start building consistency."
    if experience == "beginner":
        return "Full body", "A simple full-body session keeps the routine approachable while you build a habit."
    return "Full body", "A balanced session is a flexible option for a general fitness goal."
