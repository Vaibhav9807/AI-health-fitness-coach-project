"""Transparent health estimates; these are not diagnoses."""

ACTIVITY = {"sedentary": 1.2, "light": 1.375, "moderate": 1.55, "active": 1.725, "very_active": 1.9}


def health_metrics(profile):
    required = (profile.get("age"), profile.get("height_cm"), profile.get("weight_kg"), profile.get("sex"))
    if any(v in (None, "") for v in required):
        raise ValueError("Age, height, weight, and sex are needed to estimate these metrics.")
    age, height, weight = int(profile["age"]), float(profile["height_cm"]), float(profile["weight_kg"])
    sex = profile["sex"]
    if age < 13 or age > 100 or not 100 <= height <= 250 or not 25 <= weight <= 350 or sex not in ("female", "male"):
        raise ValueError("Enter an age from 13–100, height from 100–250 cm, weight from 25–350 kg, and select female or male for this BMR equation.")
    bmi = weight / ((height / 100) ** 2)
    # Mifflin–St Jeor; sex-specific constants are required by this equation.
    bmr = 10 * weight + 6.25 * height - 5 * age + (5 if sex == "male" else -161)
    tdee = bmr * ACTIVITY.get(profile.get("activity_level", "light"), 1.375)
    goal = profile.get("goal", "general_fitness")
    adjustment = {"weight_loss": .9, "weight_gain": 1.1, "muscle_building": 1.08, "maintain": 1, "general_fitness": 1}.get(goal, 1)
    target = tdee * adjustment
    return {"bmi": round(bmi, 1), "bmr": round(bmr), "tdee": round(tdee), "calorie_range": [round(target * .95), round(target * 1.05)],
            "disclaimer": "Estimates only, not a diagnosis or precise measurement. BMI is a screening measure and does not assess overall health."}
