"use client";

import React from "react";
import { useRouter } from "next/navigation";
import { PatientChat } from "@/components/patient/PatientChat";
import { VitalsPanel } from "@/components/clinical/VitalsPanel";
import { LabsPanel } from "@/components/clinical/LabsPanel";
import { LabOrderModal } from "@/components/clinical/LabOrderModal";
import { ActionBar } from "@/components/actions/ActionBar";
import { useSession } from "@/hooks/useSession";

interface SessionClientProps {
  sessionId: string;
}

export function SessionClient({ sessionId }: SessionClientProps) {
  const router = useRouter();
  const {
    session,
    caseData,
    orderedLabs,
    resourcesUsed,
    maxResources,
    isLoading,
    error,
    orderLabs,
    submitDiagnosis,
  } = useSession(sessionId);

  const [isLabModalOpen, setLabModalOpen] = React.useState(false);

  if (isLoading) {
    return (
      <div className="flex h-64 flex-col items-center justify-center gap-3">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-slate-200 border-t-emerald-500" />
        <p className="text-base text-slate-500">Loading session…</p>
      </div>
    );
  }

  if (!session || !caseData) {
    return (
      <div className="mx-auto max-w-md rounded-2xl border border-rose-200 bg-rose-50 p-6 text-center">
        <p className="text-base font-semibold text-rose-800">Failed to load session</p>
        <p className="mt-1 text-sm text-rose-600">{error ?? "Session not found"}</p>
      </div>
    );
  }

  return (
    // 80px header + 32px main padding (py-4 = 16px top + 16px bottom)
    <div className="flex h-[calc(100vh-112px)] gap-6 overflow-hidden">

      {/* ── Left column: fixed height, internal flex ── */}
      <div className="flex flex-1 flex-col gap-3 overflow-hidden">

        {/* Case banner — fixed */}
        <div className="flex shrink-0 items-center justify-between rounded-2xl border border-slate-200 bg-white px-6 py-3 shadow-sm">
          <div>
            <p className="text-xs font-bold uppercase tracking-widest text-slate-400">Active Case</p>
            <h1 className="mt-1 text-2xl font-bold text-slate-900">{caseData.presenting_complaint}</h1>
          </div>
          <div className="flex items-center gap-2">
            <span className="rounded-full bg-slate-100 px-3 py-1 text-base font-medium text-slate-700">
              {caseData.demographics.age}yo {caseData.demographics.gender === "M" ? "Male" : "Female"}
            </span>
            <span className={`rounded-full px-3 py-1 text-sm font-bold uppercase tracking-wide ${
              caseData.difficulty === "easy"
                ? "bg-emerald-100 text-emerald-700"
                : caseData.difficulty === "medium"
                  ? "bg-amber-100 text-amber-700"
                  : "bg-rose-100 text-rose-700"
            }`}>
              {caseData.difficulty}
            </span>
          </div>
        </div>

        {/* Chat — grows and scrolls internally */}
        <div className="min-h-0 flex-1 rounded-2xl border border-slate-200 bg-white shadow-sm">
          <PatientChat sessionId={session.session_id} />
        </div>

        {/* Actions — fixed at bottom */}
        <div className="shrink-0">
          <ActionBar
            onOrderLabs={() => setLabModalOpen(true)}
            onSubmitDiagnosis={async (payload) => {
              const res = await submitDiagnosis(payload);
              if (res) router.push(`/results/${encodeURIComponent(session.session_id)}`);
            }}
            caseDiagnoses={caseData.diagnoses}
          />
        </div>
      </div>

      {/* ── Right column: scrolls independently ── */}
      <div className="flex w-[460px] shrink-0 flex-col gap-3 overflow-y-auto pb-2">
        <VitalsPanel caseData={caseData} />
        <LabsPanel
          orderedLabs={orderedLabs}
          resourcesUsed={resourcesUsed}
          maxResources={maxResources}
          onOpenOrderModal={() => setLabModalOpen(true)}
        />
      </div>

      <LabOrderModal
        isOpen={isLabModalOpen}
        onClose={() => setLabModalOpen(false)}
        onConfirm={async (labIds) => { await orderLabs(labIds); }}
      />
    </div>
  );
}