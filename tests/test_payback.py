"""Regression tests for capital recovery over the modeled cash-flow horizon."""

import unittest

from calculations import calc_roi
from financial_summary import ai_decision_block, format_payback, payback_metric


class PaybackTests(unittest.TestCase):
    def roi(self, *, capex_per_home=300, arpu=10, years=10, churn_rate=0):
        return calc_roi(
            homes=1,
            take_rate=1,
            arpu=arpu,
            capex_per_home=capex_per_home,
            discount_rate=0,
            opex_pct=0,
            churn_rate=churn_rate,
            years=years,
        )

    def test_unrecovered_investment_is_not_reported_at_horizon(self):
        roi = self.roi(capex_per_home=1201)
        self.assertLess(sum(roi["cashflows"]), 0)
        self.assertIsNone(roi["payback"])

    def test_no_revenue_never_recovers(self):
        self.assertIsNone(self.roi(arpu=0)["payback"])

    def test_interpolates_first_recovery_year(self):
        self.assertAlmostEqual(self.roi()["payback"], 2.5)

    def test_recovery_exactly_at_horizon_remains_valid(self):
        self.assertAlmostEqual(self.roi(capex_per_home=1200)["payback"], 10.0)

    def test_zero_initial_investment_is_recovered_at_start(self):
        self.assertEqual(self.roi(capex_per_home=0)["payback"], 0.0)

    def test_empty_horizon_does_not_invent_recovery(self):
        self.assertIsNone(self.roi(years=0)["payback"])

    def test_churn_can_prevent_recovery_within_horizon(self):
        roi = self.roi(capex_per_home=300, churn_rate=0.5)
        self.assertIsNone(roi["payback"])
        self.assertEqual(roi["horizon_years"], 10)

    def test_unrecovered_result_reaches_dashboard_and_report(self):
        roi = self.roi(capex_per_home=1201)
        self.assertEqual(payback_metric(roi["payback"], roi["horizon_years"]),
                         ("Not recovered", "10-year horizon"))
        self.assertEqual(format_payback(roi["payback"], roi["horizon_years"]),
                         "Not recovered within 10 years")
        # Missing recovery must prevent an investment recommendation even when
        # other metrics are favorable or supplied by another caller.
        decision, reason = ai_decision_block(roi["payback"], npv=100, irr=20)
        self.assertEqual(decision, "decision-bad")
        self.assertIn("not recovered", reason)

    def test_recovered_result_preserves_display_and_recommendation(self):
        roi = self.roi()
        self.assertEqual(payback_metric(roi["payback"], roi["horizon_years"]),
                         ("2.5 yrs", "Fast"))
        self.assertEqual(format_payback(roi["payback"], roi["horizon_years"]),
                         "2.5 years")
        decision, _ = ai_decision_block(roi["payback"], npv=100, irr=20)
        self.assertEqual(decision, "decision-good")


if __name__ == "__main__":
    unittest.main()
