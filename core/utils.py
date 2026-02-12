import pandas as pd
import numpy as np

def normalize_columns(df: pd.DataFrame, kind: str) -> pd.DataFrame:
    df = df.copy()
    df.columns = [c.strip().lower() for c in df.columns]

    if kind == "donations":
        aliases = {
            "date": ["date", "giftdate", "contributiondate", "transactiondate", "receiveddate"],
            "amount": ["amount", "contributionamount", "giftamount", "total"],
            "donor_id": ["donor_id", "vanid", "personid", "donorid", "contactid", "id"],
            "campaign_code": ["campaign_code", "appealcode", "campaign", "sourcecode", "fundraisingcode", "appeal"],
            "channel": ["channel", "source", "medium", "fundraisingsource"],
        }
    else:
        aliases = {
            "date": ["date", "expensedate", "paiddate", "transactiondate"],
            "cost_amount": ["cost_amount", "amount", "expense", "cost", "total"],
            "campaign_code": ["campaign_code", "appealcode", "campaign", "sourcecode", "fundraisingcode", "appeal"],
            "channel": ["channel", "source", "medium"],
            "cost_type": ["cost_type", "type", "category"],
            "notes": ["notes", "memo", "description"],
        }

    def find_col(target: str):
        for c in aliases[target]:
            if c in df.columns:
                return c
        return None

    out = pd.DataFrame()

    for target in aliases:
        col = find_col(target)
        out[target] = df[col] if col else np.nan

    if kind == "donations":
        out["campaign_code"] = out["campaign_code"].fillna("UNMAPPED")
        out["channel"] = out["channel"].fillna("UNMAPPED")
    else:
        out["campaign_code"] = out["campaign_code"].fillna("UNMAPPED")
        out["channel"] = out["channel"].fillna("UNMAPPED")
        out["cost_type"] = out["cost_type"].fillna("Direct")
        out["notes"] = out["notes"].fillna("")

    return out

def ensure_datetime(df: pd.DataFrame, col: str) -> pd.DataFrame:
    df = df.copy()
    df[col] = pd.to_datetime(df[col], errors="coerce")
    df = df.dropna(subset=[col])
    return df

def month_floor(dt) -> str:
    return pd.to_datetime(dt).strftime("%Y-%m")

def segment_donors_basic(d: pd.DataFrame) -> pd.DataFrame:
    """
    Default segmentation:
    - New = first donation by donor_id within the uploaded dataset
    - Returning = otherwise
    (You can replace with a true 'prior-year retention' model later.)
    """
    d = d.copy()
    d = d.sort_values(["donor_id", "date"])
    first = d.groupby("donor_id")["date"].transform("min")
    d["donor_segment"] = (d["date"] == first).map({True: "New", False: "Returning"})
    return d

def safe_div(a: float, b: float) -> float:
    return float(a) / float(b) if b not in (0, None) else 0.0
