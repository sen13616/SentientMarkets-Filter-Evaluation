"""Phase 0 follow-up: inspect one ticker's full raw history in memory.

Answers questions the days=2 probe cannot: is score_exo served inside the
research window, are there duplicate timestamps or rows inside the 23 June to
2 July outage, what tick cadence and missing-layer pattern does the window
have, and how do score / score_raw / label relate to the sub-indices.

Prints statistics only; writes nothing to disk.
"""

from __future__ import annotations

import sys
from collections import Counter
from datetime import date, datetime, time, timedelta, timezone

import pandas as pd
from dotenv import load_dotenv

sys.path.insert(0, "scripts")
from probe_api import get  # noqa: E402  (throttled, backoff, key from .env)

TICKER = sys.argv[1] if len(sys.argv) > 1 else "AAPL"
W = {"market": 0.35, "narrative": 0.30, "influencer": 0.25, "macro": 0.10}


def band(x: float) -> str:
    x = round(x)
    return ("Strongly Bearish" if x <= 20 else "Bearish" if x <= 40 else
            "Neutral" if x <= 60 else "Bullish" if x <= 80 else "Strongly Bullish")


def main():
    load_dotenv()
    days = (datetime.now(timezone.utc).date() - date(2026, 4, 24)).days + 1
    r, s = get(f"/v1/sentiment/{TICKER}/history", params={"days": days, "interval": "raw"})
    rows = r.json()["history"]
    df = pd.DataFrame(rows)
    sub = pd.json_normalize(df.pop("sub_indices"))
    df = pd.concat([df, sub], axis=1)
    df["ts"] = pd.to_datetime(df["timestamp"], utc=True, format="ISO8601")
    df = df.sort_values("ts").reset_index(drop=True)
    print(f"{TICKER}: rows={len(df)} bytes={len(r.content)} seconds={s:.2f}")
    print("returned order newest-first:", rows[0]["timestamp"] > rows[-1]["timestamp"])

    # Periods
    def period(t):
        if t < pd.Timestamp("2026-06-23", tz="UTC"):
            return "1 research (<=22 Jun)"
        if t < pd.Timestamp("2026-07-03", tz="UTC"):
            return "2 outage (23 Jun-2 Jul)"
        if t < pd.Timestamp("2026-08-10", tz="UTC"):
            return "3 live (3 Jul-9 Aug)"
        if t < pd.Timestamp("2026-10-03", tz="UTC"):
            return "4 failures/replay (10 Aug-2 Oct)"
        return "5 after repair (>=3 Oct)"
    df["period"] = df["ts"].map(period)

    print("\nRows and score_exo coverage by period:")
    g = df.groupby("period")
    print(pd.DataFrame({
        "rows": g.size(),
        "score_exo_nonnull": g["score_exo"].apply(lambda x: x.notna().sum()),
        "first": g["ts"].min().dt.strftime("%Y-%m-%d %H:%M"),
        "last": g["ts"].max().dt.strftime("%Y-%m-%d %H:%M"),
    }).to_string())
    first_exo = df.loc[df["score_exo"].notna(), "ts"].min()
    print("first non-null score_exo:", first_exo)

    # Duplicates and gaps
    dup = df["ts"].duplicated(keep=False)
    print(f"\nexact duplicate timestamps: {dup.sum()} rows")
    gaps = df["ts"].diff().dt.total_seconds().div(60)
    near = (gaps < 5).sum()
    print(f"ticks < 5 minutes after the previous one: {near}")
    if near:
        idx = gaps[gaps < 5].index[:5]
        for i in idx:
            a, b = df.loc[i - 1], df.loc[i]
            print(f"  {a['timestamp']} score={a['score']} raw={a['score_raw']} | "
                  f"{b['timestamp']} score={b['score']} raw={b['score_raw']} conf={b['confidence']}")
    big = gaps[gaps > 120].sort_values(ascending=False).head(8)
    print("largest gaps (minutes):")
    for i, v in big.items():
        print(f"  {df.loc[i - 1, 'timestamp']} -> {df.loc[i, 'timestamp']}  {v:.0f}")

    # Research window detail
    rw = df[df["period"] == "1 research (<=22 Jun)"].copy()
    rw["date"] = rw["ts"].dt.date
    rw["tod"] = rw["ts"].dt.time
    print(f"\nResearch window rows={len(rw)} days with rows={rw['date'].nunique()}")
    in_sess = rw[(rw["tod"] >= time(14, 30)) & (rw["tod"] <= time(21, 0)) & (rw["ts"].dt.weekday < 5)]
    gs = in_sess["ts"].diff().dt.total_seconds().div(60)
    print(f"in-session tick gap median={gs[gs < 120].median():.1f} min")
    print("missing_layers combos:", Counter(tuple(x) for x in rw["missing_layers"]).most_common(8))
    for c in ["market", "narrative", "influencer", "macro"]:
        print(f"  {c}: null share={rw[c].isna().mean():.3f}")
    print("confidence distribution:", rw["confidence"].describe().round(1).to_dict())
    print("confidence < 60 share:", round((rw["confidence"] < 60).mean(), 3))

    # Ticks at or before 21:30 UTC per weekday
    wd = rw[rw["ts"].dt.weekday < 5]
    cut = wd[wd["tod"] <= time(21, 30)]
    last = cut.groupby("date")["ts"].max()
    print(f"weekdays with any row={wd['date'].nunique()}, with a tick <=21:30={last.size}")
    print("time of last tick <=21:30 (counts):",
          Counter(last.dt.strftime("%H:%M").str[:4] + "x").most_common(6))
    first_day = rw["date"].min()
    print("first day ticks:", rw.loc[rw["date"] == first_day, "timestamp"].head(3).tolist())

    # Relationship checks
    def comp(row, keys):
        present = {k: row[k] for k in keys if pd.notna(row[k])}
        if not present:
            return float("nan")
        tot = sum(W[k] for k in present)
        return sum(W[k] * v for k, v in present.items()) / tot
    rw["comp"] = rw.apply(lambda r: comp(r, W), axis=1)
    subs = rw[list(W)]
    spread = subs.max(axis=1) - subs.min(axis=1)
    capped = (subs.max(axis=1) > 85) & (subs.min(axis=1) < 30)
    rw["comp_eff"] = rw["comp"].where(~capped, rw["comp"].clip(upper=75))
    d = (rw["comp_eff"].round() - rw["score_raw"]).abs()
    print(f"\nscore_raw vs round(weighted sub-indices, capped): exact match share={(d == 0).mean():.3f}, "
          f"|diff|<=1 share={(d <= 1).mean():.3f}, max={d.max():.0f}")
    print(f"high-divergence (spread>40) share={(spread > 40).mean():.3f}, cap-trigger share={capped.mean():.3f}")
    lab_score = (rw["score"].map(band) == rw["label"]).mean()
    lab_raw = (rw["score_raw"].map(band) == rw["label"]).mean()
    print(f"label matches band(score)={lab_score:.3f}, band(score_raw)={lab_raw:.3f}")
    print(f"score != score_raw share={(rw['score'] != rw['score_raw']).mean():.3f}")
    del df, rw, rows


if __name__ == "__main__":
    main()
