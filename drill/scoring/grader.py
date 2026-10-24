class RecoveryGrader:
    def __init__(self, max_rto_seconds: float = 60.0, max_rpo_hours: float = 24.0):
        self.max_rto = max_rto_seconds
        self.max_rpo = max_rpo_hours

    def calculate_grade(self, 
                        rto_seconds: float, 
                        rpo_hours: float, 
                        critical_checks: dict[str, bool], 
                        smoke_status: str) -> dict:
        score = 100
        penalties = []

        # 1. Critical path penalties
        missing_count = sum(1 for passed in critical_checks.values() if not passed)
        if missing_count > 0:
            penalty = missing_count * 35
            score -= penalty
            penalties.append(f"{missing_count} critical file(s) missing (-{penalty} pts)")

        # 2. Smoke test integrity penalty
        if smoke_status.upper() != "PASS":
            score -= 25
            penalties.append(f"Database smoke test failed (-25 pts)")

        # 3. RTO (Restore Speed) penalty
        if rto_seconds > (self.max_rto * 2):
            score -= 20
            penalties.append(f"RTO severely exceeded target: {rto_seconds}s > {self.max_rto*2}s (-20 pts)")
        elif rto_seconds > self.max_rto:
            score -= 10
            penalties.append(f"RTO exceeded target: {rto_seconds}s > {self.max_rto}s (-10 pts)")

        # 4. RPO (Snapshot Freshness) penalty
        if rpo_hours > 72:
            score -= 25
            penalties.append(f"RPO stale: snapshot is {rpo_hours}h old (>72h) (-25 pts)")
        elif rpo_hours > self.max_rpo:
            score -= 10
            penalties.append(f"RPO exceeded target: snapshot is {rpo_hours}h old (-10 pts)")

        score = max(0, score)

        if score >= 90:
            grade = "A"
        elif score >= 80:
            grade = "B"
        elif score >= 70:
            grade = "C"
        elif score >= 60:
            grade = "D"
        else:
            grade = "F"

        return {
            "score": score,
            "grade": grade,
            "penalties": penalties
        }
