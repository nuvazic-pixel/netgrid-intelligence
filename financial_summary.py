"""Presentation helpers shared by the financial dashboard and report."""


def format_payback(payback: float | None, years: int) -> str:
    """Keep lack of capital recovery explicit in the financial report."""
    if payback is None:
        return f"Not recovered within {years} years"
    return f"{payback:.1f} years"


def payback_metric(payback: float | None, years: int) -> tuple[str, str]:
    """Return a display value and context for the dashboard metric."""
    if payback is None:
        return "Not recovered", f"{years}-year horizon"
    return f"{payback:.1f} yrs", "Fast" if payback < 7 else "Slow"


def ai_decision_block(payback: float | None, npv: float, irr: float) -> tuple[str, str]:
    if payback is None:
        return (
            'decision-bad',
            '🔴 AI Investment Decision: Capital is not recovered within the modeled horizon. '
            'Review CAPEX, demand, or subsidy assumptions before considering investment.'
        )
    if payback < 5 and npv > 0 and irr >= 15:
        return (
            'decision-good',
            '🟢 AI Investment Decision: Strong investment case. '
            'Deploy now. Commercial fundamentals are solid and capital recovery is fast.'
        )
    elif payback < 8 and npv > 0:
        return (
            'decision-mid',
            '🟡 AI Investment Decision: Viable, but optimize CAPEX, adoption, or ARPU before scale-up.'
        )
    return (
        'decision-bad',
        '🔴 AI Investment Decision: High-risk scenario. '
        'Not recommended without subsidy, redesign, or stronger demand assumptions.'
    )

