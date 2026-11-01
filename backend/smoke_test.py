"""End-to-end check of the learning loop against a real MySQL/MariaDB (uses a throwaway DB `aigenda_test`).
Run:  pip install httpx && python smoke_test.py   (XAMPP MySQL must be running)"""
import os, random
os.environ.update(DB_NAME="aigenda_test", AIGENDA_MAINTENANCE="0", RETRAIN_MIN_ROWS="100", RETRAIN_EVERY="20")
import ml, shutil, tempfile                          # keep the shipped model untouched: work on a temp copy
_tmp = tempfile.mkdtemp(); os.makedirs(os.path.join(_tmp, "data"))
shutil.copy(ml.MODEL_PATH, os.path.join(_tmp, "rf_model.joblib"))
ml.HERE, ml.MODEL_PATH = _tmp, os.path.join(_tmp, "rf_model.joblib")
import main
from fastapi.testclient import TestClient

boot = main.connect(with_db=False); boot.cursor().execute("DROP DATABASE IF EXISTS aigenda_test"); boot.close()
rnd = random.Random(1)

def auth(r): return {"Authorization": "Bearer " + r.json()["token"]}

with TestClient(main.app) as c:                      # starts lifespan: creates DB + tables, loads model
    ra = c.post("/api/register", json={"name": "Real Student", "email": "a@school.edu", "password": "secret1"})
    rt = c.post("/api/register", json={"name": "Dev", "email": "dev@test.local", "password": "secret1"})
    A, T = auth(ra), auth(rt)
    assert ra.status_code == 200 and rt.status_code == 200
    habits = {"wake": 6, "sleep": 23, "cs": 13, "ce": 15, "chrono": "morning", "hobbies": ["Gaming"],
              "adherence": 2, "distraction": 5, "stress_sleep": 4}
    for H in (A, T):
        assert c.put("/api/habits", headers=H, json=habits).status_code == 200
        for s in ["DSA", "SAD", "Networks"]:
            c.post("/api/subjects", headers=H, json={"name": s})
    g = c.post("/api/schedule/generate", headers=A); assert g.status_code == 200
    study = [x for x in g.json() if x["kind"] == "study"]
    print("today's study blocks:", [(x["hour"], x["label"]) for x in study])
    assert c.patch(f"/api/schedule/{study[0]['id']}", headers=A, json={"done": True}).status_code == 200

    # Deck use cases: summary (UC-04), reschedule conflict (UC-05), progress/streak (UC-06), goal validation (UC-10), support (UC-11)
    sm = c.get("/api/schedule/summary", headers=A).json(); assert sm["study_hours"] == len(study), sm
    assert c.patch(f"/api/schedule/{study[1]['id']}", headers=A, json={"hour": study[0]["hour"]}).status_code == 409
    assert c.get("/api/progress", headers=A).json()["streak"] >= 1
    assert c.post("/api/goals", headers=A, json={"title": "Old", "due_date": "2000-01-01"}).status_code == 422
    assert c.post("/api/goals", headers=A, json={"title": "Finish SAD", "due_date": "2999-01-01"}).status_code == 200
    assert c.post("/api/support", headers=A, json={"topic": "Sleep"}).json()["resources"]

    # Backdate history: 60 past days x 5 study blocks for the real student, 20 days for the test account
    def backdate(email, days):
        with main.db() as db:
            uid = db.one("SELECT id FROM users WHERE email=%s", (email,))["id"]
            for d in range(1, days + 1):
                for hour in rnd.sample(range(7, 23), 5):
                    peak = 8 <= hour < 12
                    db.run("INSERT INTO schedule_items(user_id,day,hour,label,kind,subject_rank,done) "
                           "VALUES(%s,CURDATE()-INTERVAL %s DAY,%s,'DSA','study',%s,%s)",
                           (uid, d, hour, rnd.randint(1, 3), int(rnd.random() < 0.30 + 0.35 * peak)))
    backdate("a@school.edu", 60); backdate("dev@test.local", 20)

    n = main.log_outcomes()
    print("outcomes logged from past days:", n)
    with main.db() as db:
        real = db.one("SELECT COUNT(*) n, SUM(1-completed) skipped FROM activity_log a JOIN users u ON u.id=a.user_id WHERE u.is_test=0")
        today = db.one("SELECT COUNT(*) n FROM activity_log WHERE day=CURDATE()")["n"]
    assert n == 400 and today == 0, "only past days are logged"
    assert real["n"] == 300 and int(real["skipped"]) > 0, "skipped blocks must be logged too"
    assert main.log_outcomes() == 0, "no duplicate logging"

    r = c.post("/api/model/retrain", headers=A)
    print("retrain:", r.status_code, r.json())
    assert r.status_code == 200 and r.json()["real_rows"] == 300, "test accounts must be excluded from training"
    st = c.get("/api/model/status", headers=A).json(); print("status:", st["real_rows_logged"], st["recent_runs"][:1])
    assert c.post("/api/schedule/generate", headers=A).status_code == 200, "scheduler works with the retrained model"
    print("ALL CHECKS PASSED")
