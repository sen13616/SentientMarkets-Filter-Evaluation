"""Phase 0: build the event list and write results/event_counts.md (counts only).

    SM_DATA_DIR=/path/to/data python -m responsiveness.scripts.event_counts

No score response around any event is computed here. The per-event table is
written to the local data root (never committed); only aggregate counts go to
results/.
"""

from __future__ import annotations

import json
from datetime import date

import numpy as np
import pandas as pd

from responsiveness import ledger, pipeline
from responsiveness.config import EVENT_END, EVENT_RAW, EVENT_START, EVENT_TYPES, RESULTS, SEED

NAMES = {"E1": "E1 earnings", "E2": "E2 large move", "E3": "E3 rating change", "E4": "E4 insider"}
DIR = {1: "up", -1: "down", 0: "none"}


def md(df: pd.DataFrame) -> str:
    return df.to_markdown(index=not isinstance(df.index, pd.RangeIndex))


def week_of(d: date) -> str:
    monday = pd.Timestamp(d) - pd.Timedelta(days=pd.Timestamp(d).weekday())
    return f"{monday:%Y-%m-%d}"


def main() -> None:
    inp = pipeline.load_inputs()
    pipeline.save_candidates(inp.cands)
    c = inp.cands
    per = c[c["in_period"]]
    kept = per[per["status"] == "kept"]
    L = ["# Event counts (Phase 0)", "",
         f"Event period: reaction sessions from {EVENT_START} to {EVENT_END}. Universe: {len(inp.tickers)} "
         "names (the first experiment's used universe). Sources: yfinance (see source_probe.md). "
         "Counts only: no score response around any event was computed to produce this file.", "",
         f"Data hash `{inp.data_hash}`.", ""]

    # Source coverage.
    man = json.loads((EVENT_RAW / "manifest.json").read_text())["tickers"]
    ok = [t for t in inp.tickers if man.get(t, {}).get("status") == "ok"]
    ins_trunc = [t for t in ok if man[t]["insider"]["rows_returned"] >= 150 and
                 (man[t]["insider"]["earliest"] is None or
                  pd.Timestamp(man[t]["insider"]["earliest"]).date() > EVENT_START)]
    no_rows = {s: sum(1 for t in ok if man[t][s]["rows_kept"] == 0) for s in ("earnings", "ratings", "insider")}
    L += ["## Source coverage", "",
          f"- Tickers fetched: {len(ok)} of {len(inp.tickers)}; failed: "
          f"{sorted(set(inp.tickers) - set(ok)) or 'none'}.",
          f"- Tickers with no rows at all on or before 22 June: earnings {no_rows['earnings']}, ratings "
          f"{no_rows['ratings']}, insider {no_rows['insider']}.",
          f"- Insider coverage truncated: {len(ins_trunc)} tickers returned the source's 150-row cap with the "
          f"oldest row after {EVENT_START}, so their insider history does not reach the start of the event "
          f"period{': ' + ', '.join(ins_trunc) if ins_trunc else ''}.", ""]

    # Headline table: kept events by type and direction.
    t = (kept.groupby(["type", "direction"]).size().unstack(fill_value=0)
         .reindex(index=list(EVENT_TYPES), columns=[1, -1], fill_value=0).rename(columns=DIR))
    t["total"] = t.sum(axis=1)
    t["stocks"] = kept.groupby("type")["ticker"].nunique().reindex(t.index).fillna(0).astype(int)
    t.loc["E1+E2 pooled"] = t.loc[["E1", "E2"]].sum()
    t.loc["E1+E2 pooled", "stocks"] = kept[kept["type"].isin(["E1", "E2"])]["ticker"].nunique()
    t.index = [NAMES.get(i, i) for i in t.index]
    below = [NAMES[ty] for ty in EVENT_TYPES if (kept["type"] == ty).sum() < 30]
    L += ["## Events kept, by type and direction", "", md(t), "",
          "**Types with fewer than 30 events: " + (", ".join(below) if below else "none") + ".**", ""]

    # Funnel: every candidate whose R is in the period, by status.
    f = per.groupby(["type", "status"]).size().unstack(fill_value=0).reindex(list(EVENT_TYPES), fill_value=0)
    order = ["kept", "no_time", "no_direction", "no_window", "e1_reaction_session", "same_type_overlap",
             "same_type_conflict", "overlap_E1", "overlap_E2", "overlap_E3"]
    f = f.reindex(columns=[o for o in order if o in f.columns] + [o for o in f.columns if o not in order],
                  fill_value=0)
    f.insert(0, "candidates", f.sum(axis=1))
    f.index = [NAMES[i] for i in f.index]
    L += ["## Drops and overlaps (candidates with R in the event period)", "",
          "Columns: `no_time` earnings release without a time of day; `no_direction` zero market-adjusted "
          "return (E1) or zero move (E2); `no_window` R-1 or R+1 outside the session list; "
          "`e1_reaction_session` an E2 session that is an E1 reaction session for the stock (excluded by "
          "definition); `same_type_overlap` window overlaps an earlier kept event of the same type and stock; "
          "`same_type_conflict` a kept event whose window holds a same-type event of the opposite direction "
          "(both dropped); `overlap_Ek` window overlaps a kept higher-ranked event Ek on the same stock.", "",
          md(f), ""]

    # E1 detail.
    e1 = per[per["type"] == "E1"]
    e1k = kept[kept["type"] == "E1"]
    hours = e1.assign(h=e1["event_time"].dt.tz_convert("America/New_York").dt.strftime("%H:%M"))["h"] \
        .value_counts().sort_index()
    agree = e1k[e1k["surprise_sign"] != 0]
    L += ["## E1 detail", "",
          f"- Releases with R in the period: {len(e1)}; time of day known: {int(e1['time_known'].sum())}; "
          f"dropped for no time: {int((~e1['time_known'].astype(bool)).sum())}.",
          "- Release times (America/New_York): " + ", ".join(f"{h} x{n}" for h, n in hours.items()) + ".",
          f"- Cross-check on kept E1 events: market-adjusted return sign agrees with EPS-surprise sign in "
          f"{int((agree['direction'] == agree['surprise_sign']).sum())} of {len(agree)} with a nonzero "
          f"surprise ({int((e1k['surprise_sign'] == 0).sum())} with zero or missing surprise).", ""]

    # Overlaps displaced by kept events.
    disp = kept[kept["overlaps_dropped"] != ""]
    L += ["## Overlaps", "",
          f"- Kept events that displaced at least one lower-ranked event: {len(disp)}.",
          "- Lower-ranked events dropped for overlap, by (kept type -> dropped type): " +
          (", ".join(f"{k} {n}" for k, n in per[per["status"].str.startswith("overlap_")]
                     .assign(k=lambda x: x["status"].str[-2:] + " -> " + x["type"])["k"].value_counts()
                     .sort_index().items()) or "none") + ".", ""]

    # By week.
    w = kept.assign(week=kept["R"].map(week_of)).groupby(["week", "type"]).size().unstack(fill_value=0) \
        .reindex(columns=list(EVENT_TYPES), fill_value=0)
    wd = kept.assign(week=kept["R"].map(week_of), d=kept["direction"].map(DIR)) \
        .groupby(["week", "type", "d"]).size().unstack(["type", "d"], fill_value=0)
    wd.columns = [f"{a} {b}" for a, b in wd.columns]
    wd = wd.reindex(columns=[f"{ty} {d}" for ty in EVENT_TYPES for d in ("up", "down")], fill_value=0)
    w.index.name = "week of (Monday)"
    wd.index.name = "week of (Monday)"
    L += ["## Kept events by week of R", "", md(w), "", "By direction:", "", md(wd), "",
          f"Events with R = 12 May (their 'before' reading is the 11 May state): "
          f"{int((kept['R'] == EVENT_START).sum())} "
          f"({', '.join(f'{k} {v}' for k, v in kept[kept['R'] == EVENT_START]['type'].value_counts().sort_index().items())}).",
          ""]

    # Events per stock.
    eps = kept.groupby("ticker").size().reindex(inp.tickers, fill_value=0)
    L += ["## Events per stock (kept, all types)", "",
          f"- Stocks with at least one kept event: {int((eps > 0).sum())} of {len(inp.tickers)}; "
          f"median {int(eps.median())}, max {int(eps.max())}.", ""]

    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "event_counts.md").write_text("\n".join(L) + "\n")
    per.groupby(["type", "status"]).size().rename("n").reset_index().to_csv(RESULTS / "event_counts.csv",
                                                                           index=False)
    head = {ty: int((kept["type"] == ty).sum()) for ty in EVENT_TYPES}
    row = ledger.append("phase0_event_counts", inp.data_hash, SEED, head)
    print("\n".join(L))
    print("ledger:", row["code_commit"], row["headline"])


if __name__ == "__main__":
    main()
