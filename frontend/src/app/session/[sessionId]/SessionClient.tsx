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
  const sendMessageRef = React.useRef<((text: string) => Promise<void>) | null>(null);

  if (isLoading) {
    return (
      <div className="flex h-[70vh] items-center justify-center text-sm text-slate-600">
        Loading session…
      </div>
    );
  }

  if (!session || !caseData) {
    return (
      <div className="rounded-3xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800">
        Failed to load session: {error ?? "Session not found"}
      </div>
    );
  }

  return (
    <div className="grid gap-4 lg:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)]">
      {error && (
        <div className="col-span-full rounded-2xl border border-amber-200 bg-amber-50 px-4 py-2 text-sm text-amber-800">
          {error}
        </div>
      )}
      <div className="flex flex-col gap-3">
        <PatientChat
          sessionId={session.session_id}
          sendMessageRef={sendMessageRef}
        />
        <ActionBar
          onOrderLabs={() => setLabModalOpen(true)}
          onAskHistoryHint={() => {
            sendMessageRef.current?.("Tell me about your medical history.");
          }}
          onSubmitDiagnosis={async (payload) => {
            const res = await submitDiagnosis(payload);
            if (res) {
              router.push(
                `/results/${encodeURIComponent(session.session_id)}`,
              );
            }
          }}
          caseDiagnoses={caseData.diagnoses}
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

