from dataclasses import dataclass, field
from app.core.session_manager import Session
from app.models import Case


@dataclass
class ScoreBreakdown:
    primary_diagnosis: int = 0       # max 40
    differential: int = 0            # max 30
    efficiency: int = 0              # max 30
    time_bonus: int = 0              # max 20 (bonus)
    total: int = 0
    feedback: list[str] = field(default_factory=list)


class ScoringEngine:
    # Scoring weights
    PRIMARY_MAX = 40
    DIFFERENTIAL_MAX = 30
    EFFICIENCY_MAX = 30
    TIME_MAX = 20  # bonus

    # Resource thresholds for efficiency scoring
    IDEAL_QUESTIONS = 8
    IDEAL_LABS = 4
    IDEAL_EXAMS = 2

    # Time thresholds (seconds)
    FAST_TIME = 300    # 5 min → full bonus
    SLOW_TIME = 900    # 15 min → no bonus

    def score_session(self, session: Session, case: Case) -> ScoreBreakdown:
        """Score a completed simulation session."""
        breakdown = ScoreBreakdown()

        breakdown.primary_diagnosis = self._score_primary(session, case, breakdown)
        breakdown.differential = self._score_differentials(session, case, breakdown)
        breakdown.efficiency = self._score_efficiency(session, breakdown)
        breakdown.time_bonus = self._score_time(session, breakdown)

        breakdown.total = (
            breakdown.primary_diagnosis
            + breakdown.differential
            + breakdown.efficiency
            + breakdown.time_bonus
        )
        return breakdown

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _score_primary(self, session: Session, case: Case, bd: ScoreBreakdown) -> int:
        if not session.submitted_diagnosis:
            bd.feedback.append("No primary diagnosis submitted — 0 points.")
            return 0

        primary_correct = self._icd9_match(
            session.submitted_diagnosis,
            [d.icd9_code for d in case.diagnoses if d.is_primary]
        )

        if primary_correct:
            bd.feedback.append("✓ Primary diagnosis is correct — full 40 points.")
            return self.PRIMARY_MAX

        # Partial credit: correct specialty / category (first 3 ICD-9 digits)
        partial = self._partial_icd9_match(
            session.submitted_diagnosis,
            [d.icd9_code for d in case.diagnoses if d.is_primary]
        )
        if partial:
            pts = int(self.PRIMARY_MAX * 0.5)
            bd.feedback.append(f"~ Primary diagnosis in correct category — {pts} points.")
            return pts

        bd.feedback.append("✗ Primary diagnosis incorrect — 0 points.")
        return 0

    def _score_differentials(self, session: Session, case: Case, bd: ScoreBreakdown) -> int:
        if not session.submitted_differentials:
            bd.feedback.append("No differentials submitted — 0 differential points.")
            return 0

        all_icd9 = [d.icd9_code for d in case.diagnoses]
        matched = sum(
            1 for diff in session.submitted_differentials
            if self._icd9_match(diff, all_icd9) or self._partial_icd9_match(diff, all_icd9)
        )

        max_possible = min(len(session.submitted_differentials), 3)
        ratio = matched / max_possible if max_possible > 0 else 0
        pts = int(self.DIFFERENTIAL_MAX * ratio)
        bd.feedback.append(f"Differentials: {matched}/{max_possible} matched — {pts} points.")
        return pts

    def _score_efficiency(self, session: Session, bd: ScoreBreakdown) -> int:
        """Penalise excess resource usage."""
        q_penalty = max(0, session.question_count - self.IDEAL_QUESTIONS) * 2
        l_penalty = max(0, session.lab_count - self.IDEAL_LABS) * 3
        e_penalty = max(0, session.exam_count - self.IDEAL_EXAMS) * 2

        total_penalty = q_penalty + l_penalty + e_penalty
        pts = max(0, self.EFFICIENCY_MAX - total_penalty)

        bd.feedback.append(
            f"Efficiency — questions: {session.question_count}, "
            f"labs: {session.lab_count}, exams: {session.exam_count} — {pts} points."
        )
        return pts

    def _score_time(self, session: Session, bd: ScoreBreakdown) -> int:
        elapsed = session.elapsed_seconds
        if elapsed <= self.FAST_TIME:
            pts = self.TIME_MAX
        elif elapsed >= self.SLOW_TIME:
            pts = 0
        else:
            # Linear interpolation
            ratio = 1 - (elapsed - self.FAST_TIME) / (self.SLOW_TIME - self.FAST_TIME)
            pts = int(self.TIME_MAX * ratio)

        minutes = int(elapsed / 60)
        bd.feedback.append(f"Time: {minutes} min — {pts} bonus points.")
        return pts

    # ------------------------------------------------------------------
    # ICD-9 matching utilities
    # ------------------------------------------------------------------

    @staticmethod
    def _normalise(code: str) -> str:
        return code.strip().upper().replace("-", "").replace(".", "")

    def _icd9_match(self, submitted: str, correct_codes: list[str]) -> bool:
        norm_sub = self._normalise(submitted)
        return any(norm_sub == self._normalise(c) for c in correct_codes)

    def _partial_icd9_match(self, submitted: str, correct_codes: list[str]) -> bool:
        """Match on first 3 characters (ICD-9 category)."""
        norm_sub = self._normalise(submitted)[:3]
        return any(norm_sub == self._normalise(c)[:3] for c in correct_codes)