# FTTH take-rate sensitivity — illustrative example

Synthetic assumptions, not observed municipal performance or an investment recommendation.
All scenarios use 3,000 homes, EUR 900 CAPEX per home, EUR 40 monthly ARPU, brownfield construction and mid risk.
Only take rate varies. The operating surplus proxy applies the existing model's fixed 30% revenue-based OPEX assumption; it is not a validated EBITDA forecast.

| Take rate | Subscribers | CAPEX (EUR) | Annual sales value (EUR) | Operating surplus proxy (EUR/year) |
| --- | --- | --- | --- | --- |
| 30% | 900 | 2,700,000 | 432,000 | 302,400 |
| 45% | 1,350 | 2,700,000 | 648,000 | 453,600 |
| 60% | 1,800 | 2,700,000 | 864,000 | 604,800 |

## Interpretation
Under these fixed assumptions, moving from 30% to 60% take rate doubles subscribers and annual sales value while modelled CAPEX stays constant.
This is an arithmetic sensitivity comparison, not evidence that a location will achieve those take rates.

## Reproduce
Run `python examples/scenario_report.py` from the repository after installing requirements.txt.
Source calculation: [calc_scenario](../calculations.py). Inputs are explicit in [the example script](../examples/scenario_report.py).

## Limits
No build phasing, capacity limits, taxes, subsidies, financing, churn or adoption ramp are modelled in this one-year example.
The labels lower/base/higher describe assumptions and carry no assigned probability.
