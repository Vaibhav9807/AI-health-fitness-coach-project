"""Train an evaluated fitness_level regression model from the supplied CSV.

The target has no documented units, so any output remains an uninterpreted
dataset score. Participant identifiers are used only to form a group holdout
and never as model features. Feature preprocessing is fitted inside the train
pipeline; no participant is shared between train and test sets.
"""
from pathlib import Path
import argparse
import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
try:
    from .data_analysis import DEFAULT_DATA
except ImportError:
    from data_analysis import DEFAULT_DATA

FEATURES=["age","weight_kg","daily_steps","activity_type","duration_minutes"]
TARGET="fitness_level"


def build_and_evaluate(csv_path=DEFAULT_DATA, output=None):
    data=pd.read_csv(csv_path,low_memory=False)
    original_rows=len(data)
    duplicate_rows=int(data.duplicated().sum())
    required=set(FEATURES+[TARGET,"participant_id"])
    missing=required-set(data.columns)
    if missing: raise ValueError("Dataset is missing required columns: "+", ".join(sorted(missing)))
    data=data.drop_duplicates().copy()
    for col in ("age","weight_kg","daily_steps","duration_minutes",TARGET):
        data[col]=pd.to_numeric(data[col],errors="coerce")
    # Invalid step counts are unknown measurements; exclude rather than turn
    # negative steps into a real low-activity training value.
    valid=data["daily_steps"].ge(0)&data[TARGET].notna()&np.isfinite(data[TARGET])
    data=data.loc[valid].copy()
    if len(data)<100 or data["participant_id"].nunique()<10:
        raise ValueError("Not enough validated labeled rows and participants to train a grouped holdout.")
    source_rows=len(data)
    # Keep a participant-balanced sample for practical local training time.
    # The held-out participants are still fully disjoint from training.
    if len(data)>120000:
        data=data.groupby("participant_id",group_keys=False).sample(n=30,random_state=42)
    X=data[FEATURES];y=data[TARGET];groups=data["participant_id"]
    numeric=["age","weight_kg","daily_steps","duration_minutes"]
    categorical=["activity_type"]
    prep=ColumnTransformer([
        ("numeric",Pipeline([("impute",SimpleImputer(strategy="median")),("scale",StandardScaler())]),numeric),
        ("category",Pipeline([("impute",SimpleImputer(strategy="most_frequent")),("encode",OneHotEncoder(handle_unknown="ignore",sparse_output=False))]),categorical),
    ])
    pipeline=Pipeline([("prepare",prep),("model",HistGradientBoostingRegressor(max_iter=60,max_leaf_nodes=15,max_bins=64,learning_rate=.08,l2_regularization=1.0,random_state=42))])
    splitter=GroupShuffleSplit(n_splits=1,test_size=.2,random_state=42)
    train,test=next(splitter.split(X,y,groups))
    pipeline.fit(X.iloc[train],y.iloc[train])
    pred=pipeline.predict(X.iloc[test])
    baseline=np.full(len(test),float(y.iloc[train].median()))
    evaluation={"mae":round(float(mean_absolute_error(y.iloc[test],pred)),4),"r2":round(float(r2_score(y.iloc[test],pred)),4),
        "baseline_median_mae":round(float(mean_absolute_error(y.iloc[test],baseline)),4),
        "test_rows":int(len(test)),"test_participants":int(groups.iloc[test].nunique()),"train_participants":int(groups.iloc[train].nunique()),
        "validated_source_rows":int(source_rows),"sampled_rows":int(len(data)),"participants_sampled":int(groups.nunique()),
        "rows_excluded_for_negative_steps_or_invalid_target":int((~valid).sum()),"exact_duplicate_rows_removed":duplicate_rows}
    artifact={"pipeline":pipeline,"target":TARGET,"features":FEATURES,"evaluation":evaluation,
        "target_note":"fitness_level units/definition not provided by source CSV; not a clinical fitness measurement."}
    if output is not None:
        output=Path(output);output.parent.mkdir(parents=True,exist_ok=True);joblib.dump(artifact,output)
    return artifact


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--csv",type=Path,default=DEFAULT_DATA)
    parser.add_argument("--output",type=Path,default=Path(__file__).resolve().parents[1]/"models"/"fitness_level.joblib")
    parser.add_argument("--no-save",action="store_true");args=parser.parse_args()
    print("Loading and inspecting",args.csv)
    result=build_and_evaluate(args.csv,None if args.no_save else args.output)
    print("Features:",result["features"]);print("Target:",result["target"],"(unit definition not provided)")
    print("Group-held-out metrics:",result["evaluation"])
    if result["evaluation"]["r2"]<=0 or result["evaluation"]["mae"]>=result["evaluation"]["baseline_median_mae"]:
        if not args.no_save and args.output.exists():args.output.unlink()
        raise SystemExit("The model did not outperform the median baseline; no deployable model retained.")
    if not args.no_save:print("Saved evaluated model:",args.output)


if __name__=="__main__":main()
