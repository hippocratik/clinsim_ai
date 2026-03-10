import { redirect } from "next/navigation";
import { api } from "@/lib/api";
import { ScoreCard } from "@/components/results/ScoreCard";
import { PathComparison } from "@/components/results/PathComparison";
import type { DiagnoseResponse } from "@/lib/types";

async function loadMockResults(sessionId: string): Promise<DiagnoseResponse> {
  // For the mock build, we just call submitDiagnosis with a placeholder payload
  // to reuse the same scoring logic.
  const res = await api.submitDiagnosis(sessionId, {
    primaryDiagnosis: {
      icd9_code: "410.11",
      description: "Acute myocardial infarction, anterolateral wall",
      is_primary: true,
    },
    differentials: [],
  });
  return res;
}

export default async function ResultsPage(props: {
  params: Promise<{ sessionId: string }>;
}) {
  const { sessionId } = await props.params;
  if (!sessionId) {
    redirect("/");
  }

  const data = await loadMockResults(sessionId);

  return (
    <div className="space-y-4">
      <div className="flex items-baseline justify-between gap-2">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">
            Case results
          </h1>
          <p className="text-sm text-slate-600">
            Session <span className="font-mono text-xs">{sessionId}</span>
          </p>
        </div>
        <a
          href="/"
          className="rounded-full bg-slate-900 px-3 py-1 text-xs font-semibold text-white shadow-sm hover:bg-slate-800"
        >
          Try another case
        </a>
      </div>

      <ScoreCard score={data.score} />
      <PathComparison
        traineePath={data.traineePath}
        optimalPath={data.optimalPath}
        learningPoints={data.learningPoints}
      />
    </div>
  );
}

