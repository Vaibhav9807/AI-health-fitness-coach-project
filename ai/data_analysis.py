"""Inspect and validate the supplied fitness dataset with Pandas."""
from pathlib import Path
import argparse
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
DEFAULT_DATA=ROOT/"data"/"health_fitness_dataset.csv"


def analyze(path=DEFAULT_DATA):
    frame=pd.read_csv(path,low_memory=False)
    summary={"path":str(path),"rows":int(len(frame)),"columns":int(len(frame.columns)),
        "column_names":frame.columns.tolist(),"dtypes":{c:str(t) for c,t in frame.dtypes.items()},
        "missing":{c:int(n) for c,n in frame.isna().sum().items()},"duplicate_rows":int(frame.duplicated().sum()),
        "date_min":str(frame["date"].min()) if "date" in frame else None,
        "date_max":str(frame["date"].max()) if "date" in frame else None,
        "participants":int(frame["participant_id"].nunique()) if "participant_id" in frame else None,
        "numeric_summary":frame.describe(include="number").round(3).to_dict(),
        "categorical_summary":{c:frame[c].value_counts(dropna=False).head(20).to_dict() for c in frame.select_dtypes(exclude="number").columns}}
    invalid={}
    for col,low,high in (("age",13,100),("height_cm",100,250),("weight_kg",25,350),("duration_minutes",1,600),("stress_level",1,10),("hours_sleep",0,24)):
        if col in frame:invalid[col]=int((~frame[col].between(low,high)).sum())
    if "daily_steps" in frame:invalid["daily_steps_negative"]=int((frame.daily_steps<0).sum())
    if "fitness_level" in frame:invalid["fitness_level_nonpositive"]=int((frame.fitness_level<=0).sum())
    summary["invalid_counts"]=invalid
    summary["participant_date_duplicates"]=int(frame.duplicated(["participant_id","date"]).sum()) if {"participant_id","date"}.issubset(frame.columns) else None
    summary["candidate_target_notes"]={
        "fitness_level":"Numeric continuous field (0.02–21.93 in inspected file), but units/definition are not documented. Potential regression label only; predictions must retain this limitation.",
        "calories_burned":"Numeric field, but inspected values (median 13; 75th percentile 20.7) are unusually small for workout rows and units are not documented; do not label estimates as verified kcal."}
    return summary


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--csv",type=Path,default=DEFAULT_DATA);args=parser.parse_args()
    result=analyze(args.csv)
    print(f"Shape: {result['rows']:,} rows × {result['columns']} columns")
    print("Columns:",", ".join(result["column_names"]))
    print("Data types:",result["dtypes"])
    print("Missing values:",result["missing"])
    print("Exact duplicate rows:",result["duplicate_rows"])
    print("Invalid values:",result["invalid_counts"])
    print("Date range:",result["date_min"],"to",result["date_max"],"; participants:",result["participants"])
    print("Numeric summary:\n",pd.DataFrame(result["numeric_summary"]).to_string())
    print("Candidate target notes:",result["candidate_target_notes"])


if __name__=="__main__":main()
