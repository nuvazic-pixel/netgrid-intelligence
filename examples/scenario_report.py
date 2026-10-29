"""Reproduce an illustrative FTTH take-rate comparison; no live data or API keys."""
from pathlib import Path
import csv
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from calculations import calc_scenario

def build_rows():
    # Synthetic assumptions: hold all inputs except take rate constant.
    rows = []
    for label, take_rate in [("Lower take rate", 0.30), ("Base take rate", 0.45), ("Higher take rate", 0.60)]:
        result = calc_scenario(3000, take_rate, 40, 900, "brownfield", "mid")
        rows.append({
            "scenario": label,
            "homes": 3000,
            "take_rate_pct": round(take_rate * 100),
            "arpu_eur_per_month": 40,
            "capex_eur_per_home": 900,
            "subscribers": result["subs"],
            "total_capex_eur": result["total_capex"],
            "annual_sales_value_eur": result["annual_rev"],
            "annual_operating_surplus_proxy_eur": result["ebitda"],
        })
    return rows

def main():
    rows = build_rows()
    destination = Path(__file__).resolve().parents[1] / "reports"
    destination.mkdir(exist_ok=True)
    with (destination / "take_rate_scenarios.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    lines = [
        "# FTTH take-rate sensitivity — illustrative example",
        "",
        "Synthetic assumptions, not observed municipal performance or an investment recommendation.",
        "All scenarios use 3,000 homes, EUR 900 CAPEX per home, EUR 40 monthly ARPU, brownfield construction and mid risk.",
        "Only take rate varies. The operating surplus proxy applies the existing model's fixed 30% revenue-based OPEX assumption; it is not a validated EBITDA forecast.",
        "",
        "| Take rate | Subscribers | CAPEX (EUR) | Annual sales value (EUR) | Operating surplus proxy (EUR/year) |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(f'| {row["take_rate_pct"]}% | {row["subscribers"]:,} | {row["total_capex_eur"]:,.0f} | {row["annual_sales_value_eur"]:,.0f} | {row["annual_operating_surplus_proxy_eur"]:,.0f} |')
    lines += [
        "",
        "## Interpretation",
        "Under these fixed assumptions, moving from 30% to 60% take rate doubles subscribers and annual sales value while modelled CAPEX stays constant.",
        "This is an arithmetic sensitivity comparison, not evidence that a location will achieve those take rates.",
        "",
        "## Reproduce",
        "Run `python examples/scenario_report.py` from the repository after installing requirements.txt.",
        "Source calculation: [calc_scenario](../calculations.py). Inputs are explicit in [the example script](../examples/scenario_report.py).",
        "",
        "## Limits",
        "No build phasing, capacity limits, taxes, subsidies, financing, churn or adoption ramp are modelled in this one-year example.",
        "The labels lower/base/higher describe assumptions and carry no assigned probability.",
        "",
    ]
    (destination / "take_rate_scenarios.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))

if __name__ == "__main__":
    main()
