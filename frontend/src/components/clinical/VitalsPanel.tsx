import type { Case } from "@/lib/types";

interface VitalsPanelProps {
  caseData: Case;
}

export function VitalsPanel({ caseData }: VitalsPanelProps) {
  const { vitals } = caseData.physical_exam;

  return (
    <section className="rounded-2xl border border-slate-200 bg-white/70 p-4 shadow-sm">
      <div className="flex items-center justify-between">
        <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          Initial Vitals
        </h3>
        <span className="rounded-full bg-rose-50 px-2 py-0.5 text-[10px] font-semibold text-rose-600 ring-1 ring-rose-100">
          Triage
        </span>
      </div>
      <dl className="mt-3 grid grid-cols-2 gap-3 text-xs sm:grid-cols-3">
        <div className="space-y-0.5">
          <dt className="text-slate-500">Heart rate</dt>
          <dd className="text-sm font-semibold text-slate-900">
            {vitals.heart_rate ? `${vitals.heart_rate} bpm` : "—"}
          </dd>
        </div>
        <div className="space-y-0.5">
          <dt className="text-slate-500">Blood pressure</dt>
          <dd className="text-sm font-semibold text-slate-900">
            {vitals.blood_pressure ?? "—"}
          </dd>
        </div>
        <div className="space-y-0.5">
          <dt className="text-slate-500">Respiratory rate</dt>
          <dd className="text-sm font-semibold text-slate-900">
            {vitals.respiratory_rate
              ? `${vitals.respiratory_rate} / min`
              : "—"}
          </dd>
        </div>
        <div className="space-y-0.5">
          <dt className="text-slate-500">Temperature</dt>
          <dd className="text-sm font-semibold text-slate-900">
            {vitals.temperature ? `${vitals.temperature.toFixed(1)} °C` : "—"}
          </dd>
        </div>
        <div className="space-y-0.5">
          <dt className="text-slate-500">SpO₂</dt>
          <dd className="text-sm font-semibold text-slate-900">
            {vitals.spo2 ? `${vitals.spo2}%` : "—"}
          </dd>
        </div>
      </dl>
      <p className="mt-3 text-xs text-slate-600">
        {caseData.physical_exam.findings}
      </p>
    </section>
  );
}

