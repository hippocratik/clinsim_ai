"use client";

import { useState } from "react";
import type { DiagnoseRequest } from "@/lib/types";
import { DiagnosisModal } from "./DiagnosisModal";

interface ActionBarProps {
  onOrderLabs: () => void;
  onSubmitDiagnosis: (payload: DiagnoseRequest) => Promise<void>;
  onAskHistoryHint?: () => void;
}

export function ActionBar({
  onOrderLabs,
  onSubmitDiagnosis,
  onAskHistoryHint,
}: ActionBarProps) {
  const [showDiagnosis, setShowDiagnosis] = useState(false);

  return (
    <>
      <div className="flex flex-wrap items-center justify-between gap-2 rounded-2xl border border-slate-200 bg-slate-50/70 px-3 py-2 text-xs shadow-sm">
        <div className="flex flex-wrap gap-1.5">
          <button
            type="button"
            onClick={onAskHistoryHint}
            className="rounded-full bg-white px-3 py-1 font-medium text-slate-800 shadow-sm ring-1 ring-slate-200 hover:bg-slate-100"
          >
            Ask history
          </button>
          <button
            type="button"
            onClick={onOrderLabs}
            className="rounded-full bg-white px-3 py-1 font-medium text-slate-800 shadow-sm ring-1 ring-slate-200 hover:bg-slate-100"
          >
            Order labs
          </button>
          <button
            type="button"
            onClick={() => setShowDiagnosis(true)}
            className="rounded-full bg-emerald-600 px-3 py-1 font-semibold text-white shadow-sm hover:bg-emerald-700"
          >
            Submit diagnosis
          </button>
        </div>
        <p className="text-[11px] text-slate-600">
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
      />
    </>
  );
}

