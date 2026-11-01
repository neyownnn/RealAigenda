"""Step 1: clean the survey export into numeric, anonymized seed profiles (no timestamps/names)."""
import re, sys, os
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "data", "survey_responses.xlsx")

# Likert items used to drive the simulator (column index in the Google Forms export)
ITEMS = {5: "sets_schedule", 6: "adherence", 8: "procrastination", 9: "balance",
         21: "distraction", 25: "focus_long", 26: "multitask_difficulty", 27: "takes_breaks", 28: "stress_sleep"}

df = pd.read_excel(SRC)
out = pd.DataFrame({name: df.iloc[:, i].astype(str).str.extract(r"^(\d)")[0].astype(int) for i, name in ITEMS.items()})
out.insert(0, "respondent", range(1, len(out) + 1))
out.to_csv(os.path.join(HERE, "data", "survey_profiles.csv"), index=False)
print(out.to_string(index=False))
print("\nAgree (>=4) 'follow schedule consistently':", int((out.adherence >= 4).sum()), "of", len(out))
