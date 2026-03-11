import type { Case } from "@/lib/types";

interface VitalsPanelProps {
  caseData: Case;
}

export function VitalsPanel({ caseData }: VitalsPanelProps) {
  const { vitals, findings } = caseData.physical_exam;

  const items = [
    {
      label: "Heart rate",
      value: vitals.heart_rate ? `${vitals.heart_rate} bpm` : "—",
      warn: vitals.heart_rate != null && (vitals.heart_rate > 100 || vitals.heart_rate < 60),
    },
    {
      label: "Blood pressure",
      value: vitals.blood_pressure ?? "—",
      warn: vitals.blood_pressure != null && parseInt(vitals.blood_pressure) > 140,
    },
    {
      label: "Respiratory rate",
      value: vitals.respiratory_rate ? `${vitals.respiratory_rate} /min` : "—",
      warn: vitals.respiratory_rate != null && (vitals.respiratory_rate > 20 || vitals.respiratory_rate < 12),
    },
    {
      label: "Temperature",
      value: vitals.temperature ? `${vitals.temperature.toFixed(1)} °C` : "—",
      warn: vitals.temperature != null && (vitals.temperature > 38.0 || vitals.temperature < 36.0),
    },
    {
      label: "SpO₂",
      value: vitals.spo2 ? `${vitals.spo2}%` : "—",
      warn: vitals.spo2 != null && vitals.spo2 < 95,
    },
  ];

  const allNull = items.every((i) => i.value === "—");

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="mb-5 flex items-center justify-between">
        <h3 className="text-base font-bold uppercase tracking-widest text-slate-500">
          Initial Vitals
        </h3>
        <span className="rounded-full bg-rose-50 px-3 py-1 text-sm font-bold uppercase tracking-wide text-rose-600 ring-1 ring-rose-200">
          Triage
        </span>
      </div>

      {allNull && !findings ? (
        <p className="text-base text-slate-500">Vitals not disclosed for this case.</p>
      ) : (
        <dl className="grid grid-cols-2 gap-3">
          {items.map(({ label, value, warn }) => (
            <div
              key={label}
              className={`rounded-xl p-4 ${warn ? "bg-rose-50 ring-1 ring-rose-200" : "bg-slate-50"}`}
            >
              <dt className="text-xs font-bold uppercase tracking-wider text-slate-500">{label}</dt>
              <dd className={`mt-2 text-2xl font-bold ${warn ? "text-rose-600" : "text-slate-900"}`}>
                {value}
                {warn && <span className="ml-1.5 text-lg">⚠</span>}
              </dd>
            </div>
          ))}
        </dl>
      )}

      {findings && (
        <div className="mt-4 rounded-xl bg-slate-50 px-4 py-3">
          <p className="mb-1.5 text-xs font-bold uppercase tracking-wider text-slate-500">Exam Findings</p>
          <p className="text-sm leading-relaxed text-slate-700">{findings}</p>
        </div>
      )}
    </section>
  );
}