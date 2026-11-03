"""Load the curated Discover datasets and their example experiments.

Run from the project root, after the SQL migrations:

    python -m backend.scripts.seed_discover

Uses the same .env as the API (database + Supabase Storage). Safe to re-run:
datasets and experiments that already exist are skipped. To add another
curated dataset, put its CSV in discover_data/ and describe it in
discover_data/manifest.json.
"""
import json
from pathlib import Path

import pandas as pd
from sqlalchemy import select

import backend.database.models  # noqa: F401  (registers every table)
from backend.database.session import SessionLocal
from backend.features.dataset.model import Dataset
from backend.features.dataset.service import upload_dataset
from backend.features.experiment.model import Experiment
from backend.features.user.model import User
from backend.run_ml_workflow import train_and_save_model

DATA_DIR = Path(__file__).resolve().parent / "discover_data"


def get_curator(db, name: str, email: str) -> User:
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        # No auth_id: nobody can sign in as the curator account.
        user = User(name=name, email=email)
        db.add(user)
        db.commit()
        db.refresh(user)
        print(f"Created curator user #{user.user_id} ({name})")
    return user


def seed_dataset(db, curator: User, spec: dict) -> Dataset:
    dataset = db.scalar(
        select(Dataset).where(
            Dataset.name == spec["name"],
            Dataset.added_by == curator.user_id,
        )
    )

    if dataset is None:
        contents = (DATA_DIR / spec["file"]).read_bytes()
        dataset = upload_dataset(
            db=db,
            name=spec["name"],
            added_by=curator.user_id,
            original_filename=spec["file"],
            contents=contents,
            is_public=True,
            description=spec["description"],
        )
        print(f"  uploaded dataset #{dataset.dataset_id}")
    else:
        print(f"  dataset #{dataset.dataset_id} already exists")

    # Keep curated details in sync with the manifest.
    dataset.description = spec["description"]
    dataset.source = spec["source"]
    dataset.tags = spec["tags"]
    dataset.is_featured = True
    dataset.is_public = True
    db.commit()
    return dataset


def seed_example(db, curator: User, dataset: Dataset, example: dict, df: pd.DataFrame):
    exists = db.scalar(
        select(Experiment).where(
            Experiment.dataset_id == dataset.dataset_id,
            Experiment.user_id == curator.user_id,
            Experiment.target == example["target"],
            Experiment.algorithm == example["algorithm"],
        )
    )
    label = f"{example['algorithm']} -> {example['target']}"
    if exists is not None:
        print(f"    {label}: already exists (#{exists.experiment_id})")
        return

    features = example["features"]
    if features == "all":
        features = [c for c in df.columns if c != example["target"]]

    categorical = example.get("categorical")
    if categorical is None:
        categorical = [
            c for c in features if not pd.api.types.is_numeric_dtype(df[c])
        ]

    result = train_and_save_model(
        db=db,
        dataset_id=dataset.dataset_id,
        user_id=curator.user_id,
        target=example["target"],
        features=features,
        categorical=categorical,
        train_size=example.get("train_size", 0.8),
        task_type=example["task_type"],
        algorithm=example["algorithm"],
        model_parameters=example.get("parameters", {}),
        persist_model=True,
        missing_strategy=example.get("missing_strategy", "impute"),
        is_public=True,
    )
    print(
        f"    {label}: experiment #{result['experiment_id']}, "
        f"model #{result['model_id']}"
    )


def main():
    manifest = json.loads((DATA_DIR / "manifest.json").read_text())

    with SessionLocal() as db:
        curator = get_curator(db, **manifest["curator"])

        for spec in manifest["datasets"]:
            print(spec["name"])
            dataset = seed_dataset(db, curator, spec)
            df = pd.read_csv(DATA_DIR / spec["file"])
            for example in spec.get("examples", []):
                try:
                    seed_example(db, curator, dataset, example, df)
                except (LookupError, ValueError) as error:
                    db.rollback()
                    print(f"    skipped {example['algorithm']} -> {example['target']}: {error}")

    print("Done.")


if __name__ == "__main__":
    main()
