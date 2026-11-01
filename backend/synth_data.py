"""Step 2: simulate study-activity outcomes for synthetic students seeded from the real survey.

The survey has no hour-by-hour completion logs, so outcomes are generated from a logistic model whose
*directions* come from the survey items and reviewed literature (see README). Each synthetic student is a
real respondent profile plus +/-1 Likert jitter, so the population mirrors the n=9 sample.
"""
import csv, math, os, random

HERE = os.path.dirname(os.path.abspath(__file__))
SURVEY = os.path.join(HERE, "data", "survey_profiles.csv")
OUT = os.path.join(HERE, "data", "synthetic_activity.csv")
PEAK = {"morning": (8, 12), "afternoon": (13, 17), "evening": (18, 22)}
# ASSUMPTION: the survey did not ask for chronotype; sample it roughly evenly.
CHRONO_P = {"morning": 0.35, "afternoon": 0.30, "evening": 0.35}
COLS = ["student_id", "hour", "in_peak", "priority", "day_load", "adherence", "distraction", "stress_sleep", "completed"]


def load_profiles():
    with open(SURVEY) as f:
        return [{k: int(v) for k, v in r.items()} for r in csv.DictReader(f)]


def clip(x):
    return max(1, min(5, x))


def p_complete(hour, in_peak, prio, load, adh, distr, stress, proc, multi, student_fx, day_fx):
    eve = 1 if 18 <= hour <= 22 else 0
    late = max(0, hour - 19) / 3
    z = (-0.10
         + 0.50 * (adh - 3)                                 # follows own schedule -> completes more
         + 0.75 * in_peak                                   # chronotype / focus window (Valladares 2018; Imam 2024)
         - 0.12 * (prio - 1)                                # lower-priority work is skipped first
         - 0.20 * (load - 4) * (1 + 0.1 * (multi - 3))      # crowded days hurt, more so if multitasking is hard
         - 0.22 * (distr - 3) * eve                         # social-media distraction bites in the evening
         - 0.18 * (stress - 3) * late                       # stress / lack of sleep hurts late sessions
         - 0.15 * (proc - 2) * (1 if load >= 5 else 0)      # last-minute habit on heavy days (Steel 2007)
         + student_fx + day_fx)
    return 1 / (1 + math.exp(-z))


def generate(n_students=600, days=30, seed=42):
    rnd = random.Random(seed)
    profiles = load_profiles()
    rows = []
    for sid in range(n_students):
        base = rnd.choice(profiles)
        v = {k: clip(base[k] + rnd.choice([-1, 0, 0, 1])) for k in base if k != "respondent"}
        chrono = rnd.choices(list(CHRONO_P), weights=CHRONO_P.values())[0]
        ps, pe = PEAK[chrono]
        s_fx = rnd.gauss(0, 0.3)
        for _ in range(days):
            load, d_fx = rnd.randint(2, 6), rnd.gauss(0, 0.4)
            for hour in rnd.sample(range(7, 23), load):
                prio = rnd.choices([1, 2, 3, 4, 5], weights=[3, 3, 2, 2, 1])[0]
                in_peak = int(ps <= hour < pe)
                p = p_complete(hour, in_peak, prio, load, v["adherence"], v["distraction"], v["stress_sleep"],
                               v["procrastination"], v["multitask_difficulty"], s_fx, d_fx)
                rows.append([sid, hour, in_peak, prio, load, v["adherence"], v["distraction"], v["stress_sleep"],
                             int(rnd.random() < p)])
    with open(OUT, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(COLS)
        w.writerows(rows)
    return rows


if __name__ == "__main__":
    r = generate()
    print(f"{len(r)} rows -> {OUT}  | overall completion rate {sum(x[-1] for x in r) / len(r):.1%}")
