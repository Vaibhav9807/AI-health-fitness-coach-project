import json
import sqlite3
from datetime import date, timedelta
import uuid
import unittest
from pathlib import Path
from backend.app import create_app
from backend.extensions import db
from backend.models import (User, WorkoutRecord, DietPlan, Recommendation, DailyTask,
    TaskCompletion, WorkoutPlan, WorkoutExercise, WorkoutCompletion, WaterGoal, WaterIntake)
from backend.calculations import health_metrics
from backend.diet_planner import meal_plan
from werkzeug.security import generate_password_hash


class CoachApiTests(unittest.TestCase):
    def setUp(self):
        self.db_dir=Path(__file__).resolve().parent/".test-data"
        self.db_dir.mkdir(exist_ok=True)
        self.db_path=self.db_dir/(uuid.uuid4().hex+".sqlite3")
        self.app=create_app({"TESTING":True,"SECRET_KEY":"test-secret","DATABASE":str(self.db_path)})
        self.apps=[self.app]
        self.extra_paths=[]
        self.client=self.app.test_client()

    def tearDown(self):
        for app in self.apps:
            with app.app_context():
                db.session.remove()
                db.engine.dispose()
        if self.db_path.exists():self.db_path.unlink()
        for path in self.extra_paths:
            if path.exists():path.unlink()

    def register(self,email="a@example.com"):
        return self.client.post("/api/register",json={"email":email,"password":"long test password"})

    def test_register_profile_login_logout(self):
        r=self.register();self.assertEqual(r.status_code,201)
        self.assertEqual(self.client.get("/api/profile").status_code,200)
        self.client.post("/api/logout")
        self.assertEqual(self.client.get("/api/profile").status_code,401)
        self.assertEqual(self.client.post("/api/login",json={"email":"a@example.com","password":"long test password"}).status_code,200)

    def test_frontend_entry_and_assets_are_served(self):
        for path in ("/", "/css/style.css", "/css/theme-dark.css", "/css/readability.css", "/js/app.js", "/js/enhancements.js"):
            response=self.client.get(path)
            self.assertEqual(response.status_code,200)
            if path=="/":self.assertIn(b"AI-Powered Personal Health",response.data)
            if path=="/js/enhancements.js":self.assertIn(b"image-fallback",response.data)
            response.close()

    def test_invalid_registration_and_profile_input(self):
        self.assertEqual(self.client.post("/api/register",json={"email":"bad","password":"short"}).status_code,400)
        self.register();r=self.client.put("/api/profile",json={"age":5});self.assertEqual(r.status_code,400)

    def test_health_metrics_and_missing_data(self):
        m=health_metrics({"age":30,"height_cm":170,"weight_kg":70,"sex":"female","activity_level":"light","goal":"general_fitness"})
        self.assertAlmostEqual(m["bmi"],24.2,places=1);self.assertGreater(m["tdee"],m["bmr"])
        with self.assertRaises(ValueError):health_metrics({})
        self.register();self.assertEqual(self.client.post("/api/health-metrics",json={}).status_code,400)

    def test_workouts_progress_and_user_isolation(self):
        self.register();w=self.client.post("/api/workouts",json={"exercise_type":"Walking","duration_minutes":25,"exercise_date":"2026-10-15"})
        self.assertEqual(w.status_code,201);self.assertEqual(len(self.client.get("/api/workouts").json["workouts"]),1)
        self.client.post("/api/progress",json={"weight_kg":69.5,"record_date":"2026-10-15"})
        self.assertEqual(len(self.client.get("/api/progress").json["weights"]),1)
        self.client.post("/api/logout");self.register("b@example.com")
        self.assertEqual(len(self.client.get("/api/workouts").json["workouts"]),0)
        self.assertEqual(len(self.client.get("/api/progress").json["weights"]),0)

    def test_profile_aware_diet_comparison_and_progress_recommendations(self):
        self.register()
        self.client.put("/api/profile",json={"age":30,"height_cm":170,"weight_kg":70,"sex":"female","activity_level":"sedentary"})
        plan=self.client.get("/api/diet-plan").json["plan"]
        self.assertIsNotNone(plan["calorie_range"])
        self.assertEqual(len(plan["calorie_range"]),2)
        self.assertIn("seated",self.client.get("/api/recommendations").json["recommendations"]["activity_note"])
        today=date.today().isoformat()
        self.client.post("/api/workouts",json={"exercise_type":"Walk","duration_minutes":20,"exercise_date":today})
        self.assertIn("logged 1 session",self.client.get("/api/recommendations").json["recommendations"]["progress_note"])
        future=(date.today()+timedelta(days=1)).isoformat()
        self.assertEqual(self.client.post("/api/workouts",json={"exercise_type":"Walk","duration_minutes":20,"exercise_date":future}).status_code,400)
        self.client.get("/api/diet-plan")
        self.client.get("/api/recommendations")
        with self.app.app_context():
            self.assertEqual(DietPlan.query.count(),2)
            self.assertEqual(Recommendation.query.count(),3)

    def test_dataset_prediction_api_is_profile_scoped(self):
        self.register()
        self.client.put("/api/profile",json={"age":32,"weight_kg":75})
        response=self.client.post("/api/model-prediction",json={"activity_type":"Walking","duration_minutes":30,"daily_steps":7500})
        self.assertEqual(response.status_code,200,response.json)
        self.assertEqual(response.json["result"]["source"],"machine_learning")
        self.assertIn("units",response.json["result"]["disclaimer"])

    def test_legacy_sqlite_records_migrate_without_losing_login(self):
        legacy=self.db_dir/(uuid.uuid4().hex+"-legacy.sqlite3")
        target=self.db_dir/(uuid.uuid4().hex+"-fitness.sqlite3")
        self.extra_paths.extend((legacy,target))
        conn=sqlite3.connect(legacy)
        conn.executescript("""
        CREATE TABLE users(id INTEGER PRIMARY KEY,email TEXT,password_hash TEXT,created_at TEXT);
        CREATE TABLE user_profiles(user_id INTEGER PRIMARY KEY,age INTEGER,height_cm REAL,weight_kg REAL,sex TEXT,activity_level TEXT,goal TEXT,dietary_preference TEXT,experience TEXT,workout_minutes INTEGER,restrictions TEXT);
        CREATE TABLE workout_records(id INTEGER PRIMARY KEY,user_id INTEGER,exercise_type TEXT,duration_minutes INTEGER,exercise_date TEXT,notes TEXT,created_at TEXT);
        CREATE TABLE weight_records(id INTEGER PRIMARY KEY,user_id INTEGER,weight_kg REAL,record_date TEXT);
        """)
        conn.execute("INSERT INTO users VALUES(1,?,?,?)",("legacy@example.com",generate_password_hash("legacy password"),"2024-01-01 00:00:00"))
        conn.execute("INSERT INTO user_profiles VALUES(1,31,172,74,'female','moderate','general_fitness','anything','beginner',30,'')")
        conn.execute("INSERT INTO workout_records VALUES(9,1,'Walking',25,'2024-01-03','old record','2024-01-03 00:00:00')")
        conn.execute("INSERT INTO weight_records VALUES(12,1,74,'2024-01-03')")
        conn.commit();conn.close()
        legacy_app=create_app({"TESTING":True,"SECRET_KEY":"test-secret","DATABASE":str(target),"LEGACY_DATABASE":str(legacy)})
        self.apps.append(legacy_app)
        client=legacy_app.test_client()
        self.assertEqual(client.post("/api/login",json={"email":"legacy@example.com","password":"legacy password"}).status_code,200)
        self.assertEqual(client.get("/api/profile").json["profile"]["age"],31)
        self.assertEqual(client.get("/api/workouts").json["workouts"][0]["id"],9)
        self.assertEqual(client.get("/api/progress").json["weights"][0]["weight_kg"],74)

    def test_diet_filters_allergens_and_chat_fallback(self):
        p=meal_plan({"dietary_preference":"vegan","restrictions":"peanuts, soy"})
        self.assertTrue(all(m["diet"]=="vegan" for m in p["meals"]))
        self.assertTrue(all(not ({"peanuts","soy"}&set(m["allergens"])) for m in p["meals"]))
        self.register();self.assertEqual(self.client.post("/api/chat",json={"message":"beginner workout"}).json["source"],"rule_based")

    def test_daily_tasks_water_and_workout_plans_are_user_scoped(self):
        self.assertEqual(self.client.get("/api/daily-tasks").status_code,401)
        self.register()
        self.client.put("/api/profile",json={"goal":"muscle_building","experience":"intermediate"})

        tasks=self.client.get("/api/daily-tasks").json
        self.assertEqual(tasks["total_count"],7)
        self.assertEqual(tasks["completed_count"],0)
        self.assertEqual(self.client.post("/api/daily-tasks",json={"title":"Stretch after lunch"}).status_code,201)
        duplicate=self.client.post("/api/daily-tasks",json={"title":"stretch AFTER lunch"})
        self.assertEqual(duplicate.status_code,409)
        task_id=self.client.get("/api/daily-tasks").json["tasks"][0]["id"]
        checked=self.client.put(f"/api/daily-tasks/{task_id}/completion",json={"completed":True})
        self.assertEqual(checked.json["completed_count"],1)
        self.assertEqual(self.client.post("/api/daily-tasks/reset",json={}).json["completed_count"],0)

        water=self.client.get("/api/water").json
        self.assertEqual(water["goal_ml"],2000)
        self.assertEqual(self.client.put("/api/water/goal",json={"goal_ml":2500}).json["water"]["goal_ml"],2500)
        entry=self.client.post("/api/water",json={"amount_ml":500})
        self.assertEqual(entry.status_code,201)
        entry_id=entry.json["water"]["entries"][0]["id"]
        corrected=self.client.patch(f"/api/water/{entry_id}",json={"amount_ml":750})
        self.assertEqual(corrected.json["water"]["intake_ml"],750)
        self.assertEqual(self.client.delete(f"/api/water/{entry_id}").json["water"]["intake_ml"],0)
        self.assertEqual(self.client.post("/api/water",json={"amount_ml":250}).status_code,201)

        catalog=self.client.get("/api/workout-plans").json
        self.assertEqual(catalog["recommended_category"],"Full body")
        self.assertEqual({c["name"] for c in catalog["categories"]},{"Chest","Back","Shoulders","Arms","Legs","Abs","Full body","Cardio"})
        plan=self.client.post("/api/workout-plans",json={"category":"Chest"})
        self.assertEqual(plan.status_code,201)
        plan_id=plan.json["plan"]["id"]
        self.assertEqual(plan.json["plan"]["exercises"][0]["sets"],3)
        exercise_id=plan.json["plan"]["exercises"][0]["id"]
        checked=self.client.put(f"/api/workout-exercises/{exercise_id}/completion",json={"completed":True}).json["plan"]
        self.assertEqual(checked["completed_count"],1)
        self.assertEqual(checked["remaining_count"],2)
        changed=self.client.patch(f"/api/workout-exercises/{exercise_id}",json={"exercise_name":"Modified press","sets":4,"repetitions":8,"duration_minutes":3,"rest_seconds":75})
        self.assertEqual(changed.status_code,200)
        self.assertEqual(changed.json["plan"]["exercises"][0]["exercise_name"],"Modified press")
        added=self.client.post(f"/api/workout-plans/{plan_id}/exercises",json={"exercise_name":"Cool down","sets":1,"repetitions":1,"duration_minutes":5,"rest_seconds":0})
        self.assertEqual(added.status_code,201)
        extra_id=added.json["plan"]["exercises"][-1]["id"]
        self.assertEqual(self.client.delete(f"/api/workout-exercises/{extra_id}").status_code,200)

        self.client.put("/api/profile",json={"goal":"weight_loss","experience":"beginner"})
        cardio_catalog=self.client.get("/api/workout-plans").json
        self.assertEqual(cardio_catalog["recommended_category"],"Cardio")
        cardio=self.client.post("/api/workout-plans",json={"category":"Cardio"}).json["plan"]
        self.assertEqual(cardio["estimated_minutes"],20)
        self.assertEqual(sum(exercise["duration_minutes"] for exercise in cardio["exercises"]),20)

        self.client.post("/api/logout")
        self.register("b@example.com")
        private_tasks=self.client.get("/api/daily-tasks").json
        self.assertEqual(private_tasks["total_count"],7)
        self.assertEqual(private_tasks["completed_count"],0)
        self.assertFalse(any(task["title"]=="Stretch after lunch" for task in private_tasks["tasks"]))
        private_water=self.client.get("/api/water").json
        self.assertEqual(private_water["goal_ml"],2000)
        self.assertEqual(private_water["intake_ml"],0)
        self.assertEqual(self.client.patch(f"/api/water/{entry_id}",json={"amount_ml":1000}).status_code,404)
        self.assertEqual(self.client.put(f"/api/daily-tasks/{task_id}/completion",json={"completed":True}).status_code,404)
        self.assertEqual(self.client.get("/api/workout-plans").json["plans"],[])
        self.assertEqual(self.client.put(f"/api/workout-exercises/{exercise_id}/completion",json={"completed":True}).status_code,404)
        self.assertEqual(self.client.delete(f"/api/workout-plans/{plan_id}").status_code,404)

    def test_water_and_exercise_validation(self):
        self.register()
        self.assertEqual(self.client.put("/api/water/goal",json={"goal_ml":50}).status_code,400)
        self.assertEqual(self.client.put("/api/water/goal",json={"goal_ml":2500.5}).status_code,400)
        self.assertEqual(self.client.post("/api/water",json={"amount_ml":0}).status_code,400)
        self.assertEqual(self.client.post("/api/water",json={"amount_ml":125.5}).status_code,400)
        self.assertEqual(self.client.post("/api/workout-plans",json={"category":"Unknown"}).status_code,400)
        plan=self.client.post("/api/workout-plans",json={"category":"Full body"}).json["plan"]
        self.assertEqual(self.client.post(f"/api/workout-plans/{plan['id']}/exercises",json={"exercise_name":"Too many reps","sets":99,"repetitions":10}).status_code,400)

    def test_account_deletion_and_auth(self):
        self.register();self.client.post("/api/workouts",json={"exercise_type":"Walk","duration_minutes":20,"exercise_date":"2026-10-15"})
        tasks=self.client.get("/api/daily-tasks").json
        self.client.put(f"/api/daily-tasks/{tasks['tasks'][0]['id']}/completion",json={"completed":True})
        self.client.get("/api/water");self.client.post("/api/water",json={"amount_ml":250})
        plan=self.client.post("/api/workout-plans",json={"category":"Full body"}).json["plan"]
        self.client.put(f"/api/workout-exercises/{plan['exercises'][0]['id']}/completion",json={"completed":True})
        self.client.get("/api/diet-plan");self.client.get("/api/recommendations")
        self.assertEqual(self.client.delete("/api/account",json={"password":"long test password","confirmation":True}).status_code,200)
        self.assertEqual(self.client.get("/api/profile").status_code,401)
        with self.app.app_context():
            self.assertEqual(User.query.count(),0)
            self.assertEqual(WorkoutRecord.query.count(),0)
            self.assertEqual(DietPlan.query.count(),0)
            self.assertEqual(Recommendation.query.count(),0)
            self.assertEqual(DailyTask.query.count(),0)
            self.assertEqual(TaskCompletion.query.count(),0)
            self.assertEqual(WorkoutPlan.query.count(),0)
            self.assertEqual(WorkoutExercise.query.count(),0)
            self.assertEqual(WorkoutCompletion.query.count(),0)
            self.assertEqual(WaterGoal.query.count(),0)
            self.assertEqual(WaterIntake.query.count(),0)


    def test_registration_with_name_and_confirm_password(self):
        # Mismatched confirm password
        r = self.client.post("/api/register", json={
            "full_name": "Vaibhav Patil",
            "email": "vaibhav@example.com",
            "password": "strongPassword123",
            "confirm_password": "differentPassword"
        })
        self.assertEqual(r.status_code, 400)
        # Valid registration with full name
        r = self.client.post("/api/register", json={
            "full_name": "Vaibhav Patil",
            "email": "vaibhav@example.com",
            "password": "strongPassword123",
            "confirm_password": "strongPassword123"
        })
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.json["user"]["full_name"], "Vaibhav Patil")
        # Me and profile reflects full name
        me = self.client.get("/api/me").json
        self.assertEqual(me["user"]["full_name"], "Vaibhav Patil")
        # Update full name
        up = self.client.put("/api/profile", json={"full_name": "Vaibhav R. Patil"})
        self.assertEqual(up.status_code, 200)
        self.assertEqual(up.json["user"]["full_name"], "Vaibhav R. Patil")

    def test_change_password(self):
        self.client.post("/api/register", json={
            "full_name": "Tester",
            "email": "chg@example.com",
            "password": "originalPassword123"
        })
        # Wrong current password
        r = self.client.put("/api/change-password", json={
            "current_password": "wrongPassword",
            "new_password": "newStrongPassword123",
            "confirm_password": "newStrongPassword123"
        })
        self.assertEqual(r.status_code, 400)
        # Correct change
        r = self.client.put("/api/change-password", json={
            "current_password": "originalPassword123",
            "new_password": "newStrongPassword123",
            "confirm_password": "newStrongPassword123"
        })
        self.assertEqual(r.status_code, 200)
        self.client.post("/api/logout")
        # Old password fails
        self.assertEqual(self.client.post("/api/login", json={"email": "chg@example.com", "password": "originalPassword123"}).status_code, 401)
        # New password succeeds
        self.assertEqual(self.client.post("/api/login", json={"email": "chg@example.com", "password": "newStrongPassword123"}).status_code, 200)

    def test_forgot_password_and_reset_workflow(self):
        self.client.post("/api/register", json={
            "full_name": "Reset User",
            "email": "reset@example.com",
            "password": "initialPassword123"
        })
        self.client.post("/api/logout")

        # Request reset link
        res = self.client.post("/api/forgot-password", json={"email": "reset@example.com"})
        self.assertEqual(res.status_code, 200)
        dev_url = res.json.get("dev_reset_url")
        self.assertIsNotNone(dev_url)
        token = dev_url.split("reset_token=")[-1]

        # Verify valid token
        v = self.client.get(f"/api/verify-reset-token?token={token}")
        self.assertEqual(v.status_code, 200)
        self.assertTrue(v.json["valid"])
        self.assertEqual(v.json["email"], "reset@example.com")

        # Verify fake token
        fake_v = self.client.get("/api/verify-reset-token?token=nonexistentToken")
        self.assertEqual(fake_v.status_code, 200)
        self.assertFalse(fake_v.json["valid"])

        # Reset password with token
        reset_res = self.client.post("/api/reset-password", json={
            "token": token,
            "password": "brandNewPassword123",
            "confirm_password": "brandNewPassword123"
        })
        self.assertEqual(reset_res.status_code, 200)

        # Single-use: using the token again must fail
        reuse_res = self.client.post("/api/reset-password", json={
            "token": token,
            "password": "anotherPassword123",
            "confirm_password": "anotherPassword123"
        })
        self.assertEqual(reuse_res.status_code, 400)

        # Login with newly reset password
        login_res = self.client.post("/api/login", json={"email": "reset@example.com", "password": "brandNewPassword123"})
        self.assertEqual(login_res.status_code, 200)

    def test_workout_update_endpoint(self):
        self.register()
        create_res = self.client.post("/api/workouts", json={
            "exercise_type": "Jogging",
            "duration_minutes": 20,
            "exercise_date": "2026-10-20",
            "notes": "Felt good"
        })
        self.assertEqual(create_res.status_code, 201)
        w_id = create_res.json["workout"]["id"]

        # Update workout
        update_res = self.client.put(f"/api/workouts/{w_id}", json={
            "exercise_type": "Running",
            "duration_minutes": 35,
            "exercise_date": "2026-10-20",
            "notes": "Pushed pace"
        })
        self.assertEqual(update_res.status_code, 200)
        self.assertEqual(update_res.json["workout"]["exercise_type"], "Running")
        self.assertEqual(update_res.json["workout"]["duration_minutes"], 35)


if __name__=="__main__":unittest.main()
