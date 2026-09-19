"""Strategy configuration loader."""

from pathlib import Path

import yaml

CONFIG_DIR = Path(__file__).parent
STRATEGY_PATH = CONFIG_DIR / "strategy.yaml"
NIFTY50_PATH = CONFIG_DIR / "nifty50.csv"


def load_strategy(path: Path | None = None) -> dict:
    with open(path or STRATEGY_PATH) as f:
        return yaml.safe_load(f)


def load_universe(path: Path | None = None) -> list[str]:
    import pandas as pd

    df = pd.read_csv(path or NIFTY50_PATH)
    return df["symbol"].tolist()
