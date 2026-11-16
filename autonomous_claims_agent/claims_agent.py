"""
Autonomous Claims Agent - simple base version
---------------------------------------------
An insurance claims agent that takes a claim from intake to a decision with no
human involvement for clear-cut cases, and escalates risky or large ones.

Pipeline:
  1. Intake & validation
  2. Policy verification
  3. Coverage check
  4. Fraud / risk scoring
  5. Payout calculation
  6. Decision (APPROVED / DENIED / ESCALATED) + full audit trail

Pure standard library. Run:  python claims_agent.py
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import date, datetime
from enum import Enum


# ----------------------------- Data models ----------------------------------
class Decision(str, Enum):
    APPROVED = "APPROVED"
    DENIED = "DENIED"
    ESCALATED = "ESCALATED_TO_HUMAN"


@dataclass
class Policy:
    policy_id: str
    holder: str
    start: date
    end: date
    coverage_limit: float
    deductible: float
    covered_types: set[str]
    active: bool = True


@dataclass
class Claim:
    policy_id: str
    claim_type: str          # e.g. "auto", "health", "property"
    incident_date: date
    amount: float
    description: str
    documents: list[str] = field(default_factory=list)
    claim_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8].upper())


@dataclass
class Result:
    claim_id: str
    decision: Decision
    payout: float
    risk_score: int
    reasons: list[str]
    audit_trail: list[dict]


# ----------------------------- Mock "database" ------------------------------
POLICIES: dict[str, Policy] = {
    "POL-1001": Policy("POL-1001", "Asha Reddy", date(2024, 1, 1), date(2027, 1, 1),
                       coverage_limit=50_000, deductible=500,
                       covered_types={"auto", "property"}),
    "POL-1002": Policy("POL-1002", "Ravi Kumar", date(2026, 10, 20), date(2027, 10, 20),
                       coverage_limit=20_000, deductible=250,
                       covered_types={"health"}),
    "POL-1003": Policy("POL-1003", "Meena Iyer", date(2023, 1, 1), date(2025, 1, 1),
                       coverage_limit=30_000, deductible=300,
                       covered_types={"auto"}, active=False),
}

# policy_id -> number of claims in the last 12 months
CLAIM_HISTORY: dict[str, int] = {"POL-1001": 4, "POL-1002": 0}


# ----------------------------- The agent ------------------------------------
class ClaimsAgent:
    AUTO_APPROVE_LIMIT = 5_000      # larger payouts always need a human
    FRAUD_ESCALATE_SCORE = 40       # risk at/above this goes to a human
    SUSPICIOUS_WORDS = ("cash", "urgent", "total loss", "no witnesses", "lost receipt")

    def __init__(self, policies=POLICIES, history=CLAIM_HISTORY):
        self.policies = policies
        self.history = history

    # --- audit helper
    @staticmethod
    def _log(trail: list[dict], step: str, outcome: str, detail: str = ""):
        trail.append({"time": datetime.now().isoformat(timespec="seconds"),
                      "step": step, "outcome": outcome, "detail": detail})

    # --- step 1
    def validate(self, c: Claim) -> list[str]:
        problems = []
        if c.amount <= 0:
            problems.append("Claim amount must be positive.")
        if c.incident_date > date.today():
            problems.append("Incident date is in the future.")
        if len(c.description.strip()) < 10:
            problems.append("Description is too short.")
        return problems

    # --- step 4
    def risk_score(self, c: Claim, p: Policy) -> tuple[int, list[str]]:
        score, flags = 0, []
        if (c.incident_date - p.start).days < 30:
            score += 30; flags.append("Incident within 30 days of policy start (+30)")
        if c.amount > 0.9 * p.coverage_limit:
            score += 25; flags.append("Amount near coverage limit (+25)")
        if self.history.get(p.policy_id, 0) >= 3:
            score += 30; flags.append("3+ claims in last 12 months (+30)")
        if not c.documents:
            score += 20; flags.append("No supporting documents (+20)")
        hits = [w for w in self.SUSPICIOUS_WORDS if w in c.description.lower()]
        if hits:
            score += 15; flags.append(f"Suspicious wording {hits} (+15)")
        return min(score, 100), flags

    # --- main entry point
    def process(self, c: Claim) -> Result:
        trail: list[dict] = []
        reasons: list[str] = []

        def finish(decision: Decision, payout=0.0, risk=0) -> Result:
            self._log(trail, "decision", decision.value, "; ".join(reasons))
            return Result(c.claim_id, decision, round(payout, 2), risk, reasons, trail)

        # 1. Validation
        problems = self.validate(c)
        self._log(trail, "validation", "fail" if problems else "pass", "; ".join(problems))
        if problems:
            reasons += problems
            return finish(Decision.DENIED)

        # 2. Policy verification
        p = self.policies.get(c.policy_id)
        if not p:
            reasons.append("Policy not found.")
            self._log(trail, "policy_check", "fail", reasons[-1])
            return finish(Decision.DENIED)
        if not p.active or not (p.start <= c.incident_date <= p.end):
            reasons.append("Policy inactive or incident outside coverage period.")
            self._log(trail, "policy_check", "fail", reasons[-1])
            return finish(Decision.DENIED)
        self._log(trail, "policy_check", "pass", f"Holder: {p.holder}")

        # 3. Coverage
        if c.claim_type not in p.covered_types:
            reasons.append(f"'{c.claim_type}' claims are not covered by this policy.")
            self._log(trail, "coverage_check", "fail", reasons[-1])
            return finish(Decision.DENIED)
        self._log(trail, "coverage_check", "pass")

        # 4. Risk
        score, flags = self.risk_score(c, p)
        self._log(trail, "risk_score", str(score), "; ".join(flags) or "no flags")

        # 5. Payout
        payout = max(0.0, min(c.amount - p.deductible, p.coverage_limit))
        self._log(trail, "payout_calc", f"{payout:.2f}",
                  f"amount {c.amount} - deductible {p.deductible}, cap {p.coverage_limit}")

        # 6. Decision
        if score >= self.FRAUD_ESCALATE_SCORE:
            reasons.append(f"Risk score {score} requires human review.")
            reasons += flags
            return finish(Decision.ESCALATED, payout, score)
        if payout > self.AUTO_APPROVE_LIMIT:
            reasons.append(f"Payout {payout:.2f} exceeds auto-approval limit.")
            return finish(Decision.ESCALATED, payout, score)

        reasons.append("All checks passed; auto-approved.")
        return finish(Decision.APPROVED, payout, score)


# ----------------------------- Demo -----------------------------------------
def demo():
    agent = ClaimsAgent()
    today = date.today()
    claims = [
        Claim("POL-1001", "property", date(2026, 9, 1), 3_200,
              "Water damage to kitchen ceiling from burst pipe.", ["photos.zip", "plumber_invoice.pdf"]),
        Claim("POL-1001", "auto", date(2026, 10, 5), 12_000,
              "Rear-end collision, bumper and trunk damage.", ["police_report.pdf"]),
        Claim("POL-1002", "health", date(2026, 11, 1), 18_500,
              "URGENT surgery, need cash payout quickly.", []),
        Claim("POL-1002", "auto", date(2026, 11, 2), 1_000,
              "Scratch on my car door in parking lot.", ["photo.jpg"]),
        Claim("POL-1003", "auto", date(2026, 6, 1), 2_000,
              "Windshield cracked by a stone on highway.", ["photo.jpg"]),
        Claim("POL-9999", "auto", today, 500,
              "Minor dent in parking lot.", ["photo.jpg"]),
    ]
    for c in claims:
        r = agent.process(c)
        print("=" * 70)
        print(f"Claim {r.claim_id} | {c.policy_id} | {c.claim_type} | claimed {c.amount:,.2f}")
        print(f"Decision : {r.decision.value}")
        print(f"Payout   : {r.payout:,.2f}   Risk: {r.risk_score}/100")
        for reason in r.reasons:
            print(f"  - {reason}")
    # Full audit trail of the last claim as JSON
    print("\nSample audit trail (last claim):")
    print(json.dumps(r.audit_trail, indent=2))


if __name__ == "__main__":
    demo()
