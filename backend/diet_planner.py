"""Small sample meal dataset with approximate nutrition estimates."""
FOODS = [
 {"meal":"Breakfast","name":"Oats with milk, banana and peanut butter","diet":"vegetarian","allergens":["peanuts","milk","gluten"],"calories":430,"protein":17,"carbs":62,"fat":13},
 {"meal":"Breakfast","name":"Tofu scramble with whole-grain toast","diet":"vegan","allergens":["soy","gluten"],"calories":390,"protein":24,"carbs":43,"fat":14},
 {"meal":"Breakfast","name":"Eggs with whole-grain toast and fruit","diet":"non_vegetarian","allergens":["eggs","gluten"],"calories":410,"protein":23,"carbs":42,"fat":16},
 {"meal":"Lunch","name":"Lentil, rice and vegetable bowl","diet":"vegan","allergens":[],"calories":560,"protein":23,"carbs":91,"fat":11},
 {"meal":"Lunch","name":"Chicken, brown rice and vegetables","diet":"non_vegetarian","allergens":[],"calories":590,"protein":42,"carbs":65,"fat":15},
 {"meal":"Lunch","name":"Chickpea and quinoa salad","diet":"vegan","allergens":[],"calories":520,"protein":21,"carbs":76,"fat":14},
 {"meal":"Evening snack","name":"Apple with unsalted almonds","diet":"vegan","allergens":["tree nuts"],"calories":220,"protein":6,"carbs":28,"fat":12},
 {"meal":"Evening snack","name":"Plain yogurt with berries","diet":"vegetarian","allergens":["milk"],"calories":190,"protein":14,"carbs":25,"fat":4},
 {"meal":"Evening snack","name":"Roasted chickpeas","diet":"vegan","allergens":[],"calories":180,"protein":9,"carbs":27,"fat":5},
 {"meal":"Dinner","name":"Bean and vegetable curry with rice","diet":"vegan","allergens":[],"calories":570,"protein":20,"carbs":88,"fat":15},
 {"meal":"Dinner","name":"Baked fish, potato and greens","diet":"non_vegetarian","allergens":["fish"],"calories":520,"protein":38,"carbs":49,"fat":17},
 {"meal":"Dinner","name":"Paneer with vegetables and roti","diet":"vegetarian","allergens":["milk","gluten"],"calories":610,"protein":29,"carbs":58,"fat":27},
]


def meal_plan(profile):
    pref = profile.get("dietary_preference", "anything").lower()
    raw = [x.strip().lower() for x in profile.get("restrictions", "").replace(";", ",").split(",") if x.strip()]
    aliases = {"peanuts":("peanut", "groundnut"), "tree nuts":("tree nut", "almond", "cashew", "walnut", "hazelnut", "pistachio", "pecan"),
               "milk":("milk", "dairy", "lactose"), "gluten":("gluten", "wheat", "barley", "rye"),
               "soy":("soy", "soya"), "eggs":("egg",), "fish":("fish",)}
    blocked = set()
    for item in raw:
        if item in {"none", "no", "n/a", "na"}: continue
        for allergen, words in aliases.items():
            if any(word in item for word in words): blocked.add(allergen)
        # Also check a phrase against food names below, e.g. "no tomatoes".
        cleaned=item.replace("allergy", "").replace("allergic to", "").replace("free", "").replace("no ", "").strip()
        if cleaned: blocked.add(cleaned)
    meals = []
    for category in ("Breakfast", "Lunch", "Evening snack", "Dinner"):
        choices = [f for f in FOODS if f["meal"] == category and not (set(f["allergens"]) & blocked)
                   and not any(term in f["name"].lower() for term in blocked if len(term) > 3)]
        if pref in ("vegan", "vegetarian"):
            choices = [f for f in choices if f["diet"] == "vegan" or (pref == "vegetarian" and f["diet"] == "vegetarian")]
        elif pref in ("non_vegetarian", "non-vegetarian"):
            choices = [f for f in choices if f["diet"] == "non_vegetarian"] or [f for f in choices if f["diet"] == "vegan"]
        if choices: meals.append(dict(choices[0]))
    totals = {k: sum(m[k] for m in meals) for k in ("calories", "protein", "carbs", "fat")}
    return {"source":"sample_food_dataset", "meals":meals, "totals":totals,
            "note":"Approximate sample estimates; portions and brands change nutrition. Review labels and avoid any food that is unsafe for you."}
