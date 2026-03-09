"use client";

import React from "react";
import { notFound } from "next/navigation";
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
      <div className="flex h-[70vh] items-center justify-center text-sm text-slate-600">
        Loading session…
      </div>
    );
  }

  if (!session || !caseData) {
    if (error) {
      return (
        <div className="rounded-3xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800">
          Failed to load session: {error}
        </div>
      );
    }
    notFound();
  }

  return (
    <div className="grid gap-4 lg:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)]">
      <div className="flex flex-col gap-3">
        <PatientChat sessionId={session.session_id} />
        <ActionBar
          onOrderLabs={() => setLabModalOpen(true)}
          onSubmitDiagnosis={async (payload) => {
            const res = await submitDiagnosis(payload);
            if (res) {
              window.location.href = `/results/${encodeURIComponent(
                session.session_id,
              )}`;
            }
          }}
        />
      </div>

      <div className="flex flex-col gap-3">
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
        onConfirm={async (labIds) => {
          await orderLabs(labIds);
        }}
      />
    </div>
  );
}

