"""
ai_swarm.py — AI Swarm Voting System for FTTH Investment Decisions
3 Agents: Conservative, Aggressive, Balanced — vote on each zone
"""

import numpy as np
from dataclasses import dataclass
from typing import Optional
from enum import Enum
import json


class Vote(Enum):
    STRONG_INVEST = "strong_invest"
    INVEST = "invest"
    HOLD = "hold"
    DELAY = "delay"
    AVOID = "avoid"


@dataclass
class AgentVote:
    agent_name: str
    agent_style: str
    vote: Vote
    confidence: float  # 0-1
    reasoning: str
    key_factors: list[str]


@dataclass
class SwarmDecision:
    gemeinde_name: str
    gemeinde_id: int
    final_decision: Vote
    consensus_score: float  # 0-1, how aligned are the agents
    votes: list[AgentVote]
    summary: str
    risk_level: str  # low, medium, high


# ============================================================
# AI AGENTS
# ============================================================

class ConservativeAgent:
    """
    Risk-averse agent. Prioritizes:
    - Low infrastructure distance
    - High existing coverage (proven demand)
    - Low competitor presence
    - Stable income demographics
    """
    
    name = "SENTINEL"
    style = "Conservative"
    icon = "🛡️"
    
    def analyze(self, zone: dict) -> AgentVote:
        score = 0
        factors = []
        
        # Distance penalty (wants low distance)
        if zone["avg_dist_m"] < 300:
            score += 25
            factors.append("Excellent infrastructure proximity")
        elif zone["avg_dist_m"] < 600:
            score += 15
            factors.append("Acceptable infrastructure distance")
        elif zone["avg_dist_m"] > 1000:
            score -= 20
            factors.append("⚠️ High infrastructure cost risk")
        
        # Existing coverage (wants proven market)
        coverage = zone.get("existing_coverage_pct", 50)
        if coverage > 60:
            score += 20
            factors.append("Strong existing market validation")
        elif coverage < 30:
            score -= 15
            factors.append("⚠️ Unproven market")
        
        # Competitor analysis
        competitor = zone.get("competitor_coverage_pct", 30)
        if competitor < 20:
            score += 15
            factors.append("Low competitive pressure")
        elif competitor > 50:
            score -= 20
            factors.append("⚠️ High competitor saturation")
        
        # Income stability
        income = zone.get("avg_household_income", 40000)
        if income > 50000:
            score += 15
            factors.append("High income demographic")
        elif income < 35000:
            score -= 10
            factors.append("Income risk factor")
        
        # Status preference (prefers deployed/partial)
        if zone["status"] == "deployed":
            score += 10
            factors.append("Expansion of proven zone")
        elif zone["status"] == "unplanned":
            score -= 15
            factors.append("⚠️ Greenfield risk")
        
        # Convert score to vote
        vote, confidence = self._score_to_vote(score)
        
        reasoning = f"{self.icon} {self.name} ({self.style}): "
        if vote in [Vote.STRONG_INVEST, Vote.INVEST]:
            reasoning += f"Risk metrics acceptable. {zone['name']} shows defensive investment characteristics."
        elif vote == Vote.HOLD:
            reasoning += f"Mixed signals for {zone['name']}. Recommend pilot before full commitment."
        else:
            reasoning += f"Risk factors exceed threshold for {zone['name']}. Capital preservation priority."
        
        return AgentVote(
            agent_name=self.name,
            agent_style=self.style,
            vote=vote,
            confidence=confidence,
            reasoning=reasoning,
            key_factors=factors
        )
    
    def _score_to_vote(self, score: int) -> tuple[Vote, float]:
        if score >= 50:
            return Vote.STRONG_INVEST, min(0.95, 0.7 + score/200)
        elif score >= 25:
            return Vote.INVEST, min(0.85, 0.6 + score/200)
        elif score >= 0:
            return Vote.HOLD, 0.5 + abs(score)/100
        elif score >= -25:
            return Vote.DELAY, 0.6 + abs(score)/150
        else:
            return Vote.AVOID, min(0.9, 0.7 + abs(score)/150)


class AggressiveAgent:
    """
    Growth-focused agent. Prioritizes:
    - High adoption potential
    - Large population / homes
    - Market gaps (low existing coverage = opportunity)
    - First-mover advantage
    """
    
    name = "VANGUARD"
    style = "Aggressive"
    icon = "⚡"
    
    def analyze(self, zone: dict) -> AgentVote:
        score = 0
        factors = []
        
        # Market size (wants big markets)
        homes = zone.get("homes", 1000)
        if homes > 10000:
            score += 30
            factors.append("Large addressable market")
        elif homes > 5000:
            score += 20
            factors.append("Solid market size")
        elif homes < 1000:
            score -= 10
            factors.append("Limited scale potential")
        
        # Coverage gap = opportunity
        coverage = zone.get("existing_coverage_pct", 50)
        gap = 100 - coverage
        if gap > 60:
            score += 25
            factors.append("Massive greenfield opportunity")
        elif gap > 40:
            score += 15
            factors.append("Significant growth headroom")
        elif gap < 20:
            score -= 10
            factors.append("Limited expansion potential")
        
        # Adoption momentum
        adoption = zone.get("adoption", 40)
        if adoption > 55:
            score += 20
            factors.append("Strong demand signal")
        elif adoption > 40:
            score += 10
            factors.append("Healthy adoption baseline")
        
        # Population density (urban = faster ROI)
        density = zone.get("pop_density_km2", 200)
        if density > 500:
            score += 15
            factors.append("High-density deployment efficiency")
        
        # First-mover vs competitor
        competitor = zone.get("competitor_coverage_pct", 30)
        if zone["status"] in ["planned", "unplanned"] and competitor < 30:
            score += 20
            factors.append("First-mover advantage available")
        
        # Convert score to vote
        vote, confidence = self._score_to_vote(score)
        
        reasoning = f"{self.icon} {self.name} ({self.style}): "
        if vote in [Vote.STRONG_INVEST, Vote.INVEST]:
            reasoning += f"Growth metrics strong. {zone['name']} represents expansion opportunity."
        elif vote == Vote.HOLD:
            reasoning += f"Moderate potential in {zone['name']}. Consider strategic timing."
        else:
            reasoning += f"Growth ceiling limited in {zone['name']}. Seek higher-yield alternatives."
        
        return AgentVote(
            agent_name=self.name,
            agent_style=self.style,
            vote=vote,
            confidence=confidence,
            reasoning=reasoning,
            key_factors=factors
        )
    
    def _score_to_vote(self, score: int) -> tuple[Vote, float]:
        # Aggressive agent has lower threshold for investment
        if score >= 40:
            return Vote.STRONG_INVEST, min(0.95, 0.7 + score/200)
        elif score >= 15:
            return Vote.INVEST, min(0.85, 0.6 + score/200)
        elif score >= -10:
            return Vote.HOLD, 0.5 + abs(score)/100
        elif score >= -30:
            return Vote.DELAY, 0.6 + abs(score)/150
        else:
            return Vote.AVOID, min(0.9, 0.7 + abs(score)/150)


class BalancedAgent:
    """
    ROI-optimized agent. Prioritizes:
    - NPV / payback period estimation
    - CAPEX efficiency (distance vs homes ratio)
    - Revenue potential vs risk balance
    """
    
    name = "ORACLE"
    style = "Balanced"
    icon = "⚖️"
    
    def analyze(self, zone: dict) -> AgentVote:
        score = 0
        factors = []
        
        # CAPEX efficiency: homes per meter of infrastructure
        homes = zone.get("homes", 1000)
        distance = zone.get("avg_dist_m", 500)
        efficiency = homes / max(distance, 100)
        
        if efficiency > 15:
            score += 25
            factors.append("Excellent CAPEX efficiency")
        elif efficiency > 8:
            score += 15
            factors.append("Good cost-to-coverage ratio")
        elif efficiency < 3:
            score -= 20
            factors.append("⚠️ Poor unit economics")
        
        # Revenue potential (adoption × homes × income proxy)
        adoption = zone.get("adoption", 40)
        income = zone.get("avg_household_income", 40000)
        revenue_score = (adoption / 100) * homes * (income / 40000)
        
        if revenue_score > 5000:
            score += 20
            factors.append("Strong revenue projection")
        elif revenue_score > 2000:
            score += 10
            factors.append("Moderate revenue potential")
        else:
            score -= 5
            factors.append("Limited revenue upside")
        
        # Payback proxy: lower distance + higher adoption = faster payback
        payback_proxy = (100 - adoption) + (distance / 20)
        if payback_proxy < 70:
            score += 15
            factors.append("Fast payback trajectory")
        elif payback_proxy > 120:
            score -= 15
            factors.append("⚠️ Extended payback period")
        
        # Market maturity balance
        coverage = zone.get("existing_coverage_pct", 50)
        if 30 < coverage < 70:
            score += 10
            factors.append("Optimal market maturity")
        
        # Risk-adjusted return
        competitor = zone.get("competitor_coverage_pct", 30)
        if competitor < 40 and adoption > 35:
            score += 10
            factors.append("Favorable risk-reward profile")
        
        # Convert score to vote
        vote, confidence = self._score_to_vote(score)
        
        reasoning = f"{self.icon} {self.name} ({self.style}): "
        if vote in [Vote.STRONG_INVEST, Vote.INVEST]:
            reasoning += f"ROI metrics favorable. {zone['name']} optimizes risk-adjusted returns."
        elif vote == Vote.HOLD:
            reasoning += f"Marginal economics in {zone['name']}. Monitor for improved conditions."
        else:
            reasoning += f"Unit economics unfavorable for {zone['name']}. Capital better deployed elsewhere."
        
        return AgentVote(
            agent_name=self.name,
            agent_style=self.style,
            vote=vote,
            confidence=confidence,
            reasoning=reasoning,
            key_factors=factors
        )
    
    def _score_to_vote(self, score: int) -> tuple[Vote, float]:
        if score >= 45:
            return Vote.STRONG_INVEST, min(0.95, 0.7 + score/200)
        elif score >= 20:
            return Vote.INVEST, min(0.85, 0.6 + score/200)
        elif score >= -5:
            return Vote.HOLD, 0.5 + abs(score)/100
        elif score >= -25:
            return Vote.DELAY, 0.6 + abs(score)/150
        else:
            return Vote.AVOID, min(0.9, 0.7 + abs(score)/150)


# ============================================================
# SWARM COORDINATOR
# ============================================================

class SwarmCoordinator:
    """Orchestrates multi-agent voting and consensus building."""
    
    def __init__(self):
        self.agents = [
            ConservativeAgent(),
            AggressiveAgent(),
            BalancedAgent(),
        ]
    
    def analyze_zone(self, zone: dict) -> SwarmDecision:
        """Run all agents on a zone and produce consensus decision."""
        votes = [agent.analyze(zone) for agent in self.agents]
        
        # Calculate consensus
        vote_values = {
            Vote.STRONG_INVEST: 2,
            Vote.INVEST: 1,
            Vote.HOLD: 0,
            Vote.DELAY: -1,
            Vote.AVOID: -2,
        }
        
        # Weighted average by confidence
        total_weight = sum(v.confidence for v in votes)
        weighted_score = sum(
            vote_values[v.vote] * v.confidence for v in votes
        ) / total_weight
        
        # Determine final decision
        if weighted_score >= 1.3:
            final = Vote.STRONG_INVEST
        elif weighted_score >= 0.5:
            final = Vote.INVEST
        elif weighted_score >= -0.3:
            final = Vote.HOLD
        elif weighted_score >= -1.0:
            final = Vote.DELAY
        else:
            final = Vote.AVOID
        
        # Consensus score: how aligned are the agents?
        vote_spread = np.std([vote_values[v.vote] for v in votes])
        consensus = max(0, 1 - vote_spread / 2)
        
        # Risk level
        if consensus > 0.7 and final in [Vote.STRONG_INVEST, Vote.INVEST]:
            risk_level = "low"
        elif consensus > 0.5:
            risk_level = "medium"
        else:
            risk_level = "high"
        
        # Generate summary
        summary = self._generate_summary(zone, votes, final, consensus)
        
        return SwarmDecision(
            gemeinde_name=zone["name"],
            gemeinde_id=zone.get("id", 0),
            final_decision=final,
            consensus_score=round(consensus, 2),
            votes=votes,
            summary=summary,
            risk_level=risk_level,
        )
    
    def _generate_summary(self, zone: dict, votes: list[AgentVote], 
                          final: Vote, consensus: float) -> str:
        """Generate executive summary of swarm decision."""
        
        decision_text = {
            Vote.STRONG_INVEST: "STRONG BUY — Immediate deployment recommended",
            Vote.INVEST: "BUY — Include in Phase 1 rollout",
            Vote.HOLD: "HOLD — Monitor and reassess in 6 months",
            Vote.DELAY: "WAIT — Defer until market conditions improve",
            Vote.AVOID: "PASS — Do not allocate capital",
        }
        
        consensus_text = "unanimous" if consensus > 0.85 else "strong" if consensus > 0.6 else "split"
        
        summary = f"**{zone['name']}**: {decision_text[final]}\n\n"
        summary += f"Consensus: {consensus_text} ({consensus:.0%})\n\n"
        summary += "**Agent Breakdown:**\n"
        
        for v in votes:
            icon = "🛡️" if v.agent_style == "Conservative" else "⚡" if v.agent_style == "Aggressive" else "⚖️"
            summary += f"- {icon} **{v.agent_name}**: {v.vote.value.upper()} ({v.confidence:.0%})\n"
        
        return summary
    
    def analyze_all_zones(self, zones: list[dict]) -> list[SwarmDecision]:
        """Analyze multiple zones and rank by investment priority."""
        decisions = [self.analyze_zone(zone) for zone in zones]
        
        # Sort by: final decision strength, then consensus
        vote_priority = {
            Vote.STRONG_INVEST: 0,
            Vote.INVEST: 1,
            Vote.HOLD: 2,
            Vote.DELAY: 3,
            Vote.AVOID: 4,
        }
        
        decisions.sort(key=lambda d: (vote_priority[d.final_decision], -d.consensus_score))
        return decisions


def get_swarm_recommendation(zone: dict) -> SwarmDecision:
    """Convenience function for single zone analysis."""
    coordinator = SwarmCoordinator()
    return coordinator.analyze_zone(zone)


def get_portfolio_analysis(zones: list[dict]) -> list[SwarmDecision]:
    """Analyze entire portfolio of zones."""
    coordinator = SwarmCoordinator()
    return coordinator.analyze_all_zones(zones)


if __name__ == "__main__":
    # Test with sample zone
    test_zone = {
        "id": 1,
        "name": "Landsberg am Lech",
        "homes": 12000,
        "adoption": 52,
        "avg_dist_m": 350,
        "existing_coverage_pct": 65,
        "avg_household_income": 45000,
        "competitor_coverage_pct": 25,
        "pop_density_km2": 774,
        "status": "partial",
    }
    
    decision = get_swarm_recommendation(test_zone)
    
    print("=" * 60)
    print("AI SWARM ANALYSIS")
    print("=" * 60)
    print(f"\nZone: {decision.gemeinde_name}")
    print(f"Final Decision: {decision.final_decision.value.upper()}")
    print(f"Consensus: {decision.consensus_score:.0%}")
    print(f"Risk Level: {decision.risk_level}")
    print("\n" + decision.summary)
    
    print("\nDetailed Agent Analysis:")
    for vote in decision.votes:
        print(f"\n{vote.agent_name} ({vote.agent_style}):")
        print(f"  Vote: {vote.vote.value}")
        print(f"  Confidence: {vote.confidence:.0%}")
        print(f"  Key Factors: {', '.join(vote.key_factors)}")
