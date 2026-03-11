"use client";

import { useState } from "react";
import type { DiagnoseRequest, Diagnosis } from "@/lib/types";
import { DiagnosisModal } from "./DiagnosisModal";

interface ActionBarProps {
  onOrderLabs: () => void;
  onSubmitDiagnosis: (payload: DiagnoseRequest) => Promise<void>;
  onAskHistoryHint?: () => void;
  caseDiagnoses: Diagnosis[];
}

export function ActionBar({
  onOrderLabs,
  onSubmitDiagnosis,
  onAskHistoryHint,
  caseDiagnoses,
}: ActionBarProps) {
  const [showDiagnosis, setShowDiagnosis] = useState(false);

  return (
    <>
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-slate-200 bg-white px-6 py-3 shadow-sm">
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={onAskHistoryHint}
            className="flex items-center gap-2 rounded-xl border border-slate-200 bg-slate-50 px-4 py-2.5 text-base font-semibold text-slate-700 transition hover:bg-slate-100"
          >
            📋 Ask history
          </button>
          <button
            type="button"
            onClick={onOrderLabs}
            className="flex items-center gap-2 rounded-xl border border-slate-200 bg-slate-50 px-4 py-2.5 text-base font-semibold text-slate-700 transition hover:bg-slate-100"
          >
            🧪 Order labs
          </button>
          <button
            type="button"
            onClick={() => setShowDiagnosis(true)}
            className="flex items-center gap-2 rounded-xl bg-emerald-600 px-5 py-2.5 text-base font-bold text-white shadow-sm transition hover:bg-emerald-700"
          >
            ✓ Submit diagnosis
          </button>
        </div>
        <p className="text-sm text-slate-400">
          Each action has a cost. Aim for fast, focused reasoning.
        </p>
      </div>

      <DiagnosisModal
        isOpen={showDiagnosis}
        onClose={() => setShowDiagnosis(false)}
        onSubmit={async (payload: DiagnoseRequest) => {
          await onSubmitDiagnosis(payload);
          setShowDiagnosis(false);
        }}
        caseDiagnoses={caseDiagnoses}
      />
    </>
  );
}