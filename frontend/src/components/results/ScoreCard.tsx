import type { CaseScore } from "@/lib/types";

interface ScoreCardProps {
  score: CaseScore;
}

export function ScoreCard({ score }: ScoreCardProps) {
  const totalScore =
    score.diagnostic_accuracy * 40 +
    score.differential_score * 30 +
    score.efficiency_score * 30;

  return (
    <section className="rounded-3xl border border-slate-200 bg-white/80 p-5 shadow-sm">
      <h2 className="text-sm font-semibold text-slate-900">
        Case performance summary
      </h2>
      <p className="mt-1 text-xs text-slate-500">
        Scores are normalized from 0–100 based on diagnostic accuracy,
        efficiency, and time to diagnosis.
      </p>

      <div className="mt-4 grid gap-4 text-sm sm:grid-cols-4">
        <div>
          <p className="text-[11px] uppercase tracking-wide text-slate-500">
            Overall
          </p>
          <p className="mt-1 text-2xl font-semibold text-slate-900">
            {Math.round(totalScore)}
          </p>
        </div>
        <div>
          <p className="text-[11px] uppercase tracking-wide text-slate-500">
            Primary diagnosis
          </p>
          <p className="mt-1 text-lg font-semibold text-slate-900">
            {score.primary_diagnosis_correct ? "Correct" : "Missed"}
          </p>
        </div>
        <div>
          <p className="text-[11px] uppercase tracking-wide text-slate-500">
            Diagnostic reasoning
          </p>
          <p className="mt-1 text-lg font-semibold text-slate-900">
            {Math.round(score.differential_score * 100)}
          </p>
        </div>
        <div>
          <p className="text-[11px] uppercase tracking-wide text-slate-500">
            Efficiency
          </p>
          <p className="mt-1 text-lg font-semibold text-slate-900">
            {Math.round(score.efficiency_score * 100)}
          </p>
        </div>
      </div>

      <div className="mt-4 grid gap-3 text-xs sm:grid-cols-2">
        <div className="rounded-2xl bg-slate-50 px-3 py-2">
          <p className="font-medium text-slate-800">Time to diagnosis</p>
          <p className="mt-0.5 text-slate-600">
            {Math.round(score.time_to_diagnosis_seconds / 60)} minutes from
            first interaction to final diagnosis.
          </p>
        </div>
        <div className="rounded-2xl bg-slate-50 px-3 py-2">
          <p className="font-medium text-slate-800">Resource use</p>
          <p className="mt-0.5 text-slate-600">
            {score.labs_ordered} labs ordered · {score.optimal_labs} considered
            essential for this case.
          </p>
        </div>
      </div>
    </section>
  );
}

