"""Random Forest: predicts P(student completes a scheduled study activity).
Pre-trained on survey-seeded synthetic data (synth_data.py); retrain() blends in real activity_log rows."""
import csv, json, os, random
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, roc_auc_score
from sklearn.model_selection import GroupShuffleSplit

HERE = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.environ.get("AIGENDA_MODEL_PATH", os.path.join(HERE, "rf_model.joblib"))
METRICS_PATH = os.path.join(HERE, "data", "model_metrics.json")
SYNTH = os.path.join(HERE, "data", "synthetic_activity.csv")
SURVEY = os.path.join(HERE, "data", "survey_profiles.csv")
FEATURES = ["hour", "in_peak", "priority", "day_load", "adherence", "distraction", "stress_sleep"]


def survey_defaults() -> dict:
    """Used when a student's own profile is unknown (cold start): the survey's mean answers."""
    with open(SURVEY) as f:
        rows = list(csv.DictReader(f))
    m = lambda k: sum(int(r[k]) for r in rows) / len(rows)
    return {"day_load": 4, "adherence": m("adherence"), "distraction": m("distraction"), "stress_sleep": m("stress_sleep")}


def load_synthetic():
    with open(SYNTH) as f:
        rows = list(csv.DictReader(f))
    return ([[float(r[c]) for c in FEATURES] for r in rows], [int(r["completed"]) for r in rows],
            [int(r["student_id"]) for r in rows])


def fit(X, y, w=None):
    clf = RandomForestClassifier(n_estimators=200, max_depth=8, min_samples_leaf=20, random_state=42, n_jobs=-1)
    return clf.fit(X, y, sample_weight=w)


def train():
    X, y, groups = load_synthetic()
    tr, te = next(GroupShuffleSplit(test_size=0.2, random_state=42).split(X, y, groups))  # hold out whole students
    clf = fit([X[i] for i in tr], [y[i] for i in tr])
    Xt, yt = [X[i] for i in te], [y[i] for i in te]
    proba = clf.predict_proba(Xt)[:, 1]
    metrics = {"rows": len(X), "test_accuracy": round(accuracy_score(yt, proba > 0.5), 3),
               "test_roc_auc": round(roc_auc_score(yt, proba), 3),
               "majority_baseline": round(max(sum(yt), len(yt) - sum(yt)) / len(yt), 3),
               "feature_importance": {f: round(float(v), 3) for f, v in zip(FEATURES, clf.feature_importances_)},
               "note": "Scored on held-out SYNTHETIC students; real-world accuracy is unknown until real logs exist."}
    final = fit(X, y)  # refit on everything for deployment
    bundle = {"model": final, "features": FEATURES, "defaults": survey_defaults(), "metrics": metrics}
    joblib.dump(bundle, MODEL_PATH)
    json.dump(metrics, open(METRICS_PATH, "w"), indent=2)
    return bundle


def load():
    return joblib.load(MODEL_PATH) if os.path.exists(MODEL_PATH) else None


def scorer_from(bundle, overrides=None):
    """Returns f(hour, in_peak, priority) -> P(complete). Other features come from the student's own values
    (overrides) when known, else the survey-mean defaults."""
    if bundle is None:
        return None
    d, clf = {**bundle["defaults"], **(overrides or {})}, bundle["model"]
    return lambda hour, in_peak, prio: float(clf.predict_proba(
        [[hour, in_peak, prio, d["day_load"], d["adherence"], d["distraction"], d["stress_sleep"]]])[0][1])


def retrain_from_rows(rows, min_rows=200, real_weight=5.0, seed=42):
    """rows: (hour, in_peak, priority, day_load, adherence, distraction, stress_sleep, completed) from activity_log.
    Blends real outcomes (weighted up) with the synthetic base, and measures accuracy on held-out REAL rows."""
    if len(rows) < min_rows:
        return None
    d = survey_defaults()
    pick = lambda v, k: float(v) if v is not None else float(d[k])
    Xr = [[float(h), float(ip), float(pr if pr is not None else 3), pick(ld, "day_load"),
           pick(ad, "adherence"), pick(di, "distraction"), pick(st, "stress_sleep")]
          for h, ip, pr, ld, ad, di, st, _ in rows]
    yr = [int(r[-1]) for r in rows]
    Xs, ys, _ = load_synthetic()

    idx = list(range(len(Xr)))
    random.Random(seed).shuffle(idx)
    cut = int(0.8 * len(idx))
    tr, te = idx[:cut], idx[cut:]
    metrics = {"real_rows": len(rows), "real_test_rows": len(te)}
    eval_clf = fit(Xs + [Xr[i] for i in tr], ys + [yr[i] for i in tr],
                   [1.0] * len(Xs) + [real_weight] * len(tr))
    yt = [yr[i] for i in te]
    if 0 < sum(yt) < len(yt):  # AUC needs both classes present
        proba = eval_clf.predict_proba([Xr[i] for i in te])[:, 1]
        metrics["real_test_accuracy"] = round(float(accuracy_score(yt, proba > 0.5)), 3)
        metrics["real_test_auc"] = round(float(roc_auc_score(yt, proba)), 3)
    final = fit(Xs + Xr, ys + yr, [1.0] * len(Xs) + [real_weight] * len(Xr))
    bundle = {"model": final, "features": FEATURES, "defaults": d, "metrics": metrics}
    joblib.dump(bundle, MODEL_PATH)
    json.dump(metrics, open(os.path.join(HERE, "data", "model_metrics_retrained.json"), "w"), indent=2)
    return bundle


if __name__ == "__main__":
    b = train()
    print(json.dumps(b["metrics"], indent=2))
