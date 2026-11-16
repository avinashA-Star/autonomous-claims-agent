# Autonomous Claims Agent

A simple base project: an insurance claims agent that takes a claim from intake
to a decision (APPROVED / DENIED / ESCALATED_TO_HUMAN) with a full audit trail.

## Pipeline
1. Validation  2. Policy check  3. Coverage check  4. Risk scoring  5. Payout calculation  6. Decision

## Run
    python claims_agent.py          # runs the demo with 6 sample claims
    python -m unittest discover tests   # runs the tests

Requires Python 3.9+. No external packages.

## Use in your own code
    from claims_agent import ClaimsAgent, Claim
    from datetime import date

    agent = ClaimsAgent()
    result = agent.process(Claim("POL-1001", "property", date(2026, 10, 10), 2500,
                                 "Storm damaged the roof tiles.", ["photo.jpg"]))
    print(result.decision, result.payout, result.reasons)

## Configuration (in ClaimsAgent)
- AUTO_APPROVE_LIMIT = 5000   (larger payouts go to a human)
- FRAUD_ESCALATE_SCORE = 40   (risk at/above this goes to a human)

## Next steps
Database (SQLite/PostgreSQL), FastAPI endpoint, Claude API for reading claim documents, human review queue.
