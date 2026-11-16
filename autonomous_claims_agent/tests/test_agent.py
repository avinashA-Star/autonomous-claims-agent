import sys, os, unittest
from datetime import date
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from claims_agent import ClaimsAgent, Claim, Decision


class TestAgent(unittest.TestCase):
    def setUp(self):
        self.agent = ClaimsAgent()

    def test_auto_approve(self):
        c = Claim("POL-1001", "property", date(2026, 9, 1), 3200,
                  "Water damage to kitchen ceiling.", ["photo.jpg", "invoice.pdf"])
        r = self.agent.process(c)
        self.assertEqual(r.decision, Decision.APPROVED)
        self.assertEqual(r.payout, 2700)

    def test_large_payout_escalated(self):
        c = Claim("POL-1001", "auto", date(2026, 10, 5), 12000,
                  "Rear-end collision, bumper damage.", ["report.pdf"])
        self.assertEqual(self.agent.process(c).decision, Decision.ESCALATED)

    def test_high_risk_escalated(self):
        c = Claim("POL-1002", "health", date(2026, 11, 1), 18500,
                  "URGENT surgery, need cash payout.", [])
        self.assertEqual(self.agent.process(c).decision, Decision.ESCALATED)

    def test_not_covered_denied(self):
        c = Claim("POL-1002", "auto", date(2026, 11, 2), 1000,
                  "Scratch on car door in parking.", ["p.jpg"])
        self.assertEqual(self.agent.process(c).decision, Decision.DENIED)

    def test_unknown_policy_denied(self):
        c = Claim("POL-9999", "auto", date(2026, 11, 2), 500,
                  "Minor dent in parking lot.", ["p.jpg"])
        self.assertEqual(self.agent.process(c).decision, Decision.DENIED)

    def test_invalid_amount_denied(self):
        c = Claim("POL-1001", "auto", date(2026, 9, 1), -5,
                  "Negative amount claim here.", ["p.jpg"])
        self.assertEqual(self.agent.process(c).decision, Decision.DENIED)


if __name__ == "__main__":
    unittest.main()
