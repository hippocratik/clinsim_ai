import Link from "next/link";
import { api } from "@/lib/api";
import type { Case, Difficulty } from "@/lib/types";

async function loadCases(): Promise<Case[]> {
  return api.getCases();
}

const difficultyLabels: Record<Difficulty, string> = {
  easy: "Easy",
  medium: "Medium",
  hard: "Hard",
};

export default async function Home() {
  const apiMode = process.env.NEXT_PUBLIC_API_MODE ?? "mock";
  const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "";

  let cases: Case[];
  try {
    cases = await loadCases();
  } catch (err) {
    const message = err instanceof Error ? err.message : "Failed to load cases";
    return (
      <div className="space-y-4">
        <section className="rounded-3xl border border-rose-200 bg-rose-50 p-5">
          <h1 className="text-xl font-semibold text-rose-900">Case library</h1>
          <p className="mt-2 text-sm text-rose-800">
            Could not load cases: {message}
          </p>
          <p className="mt-1 text-xs text-rose-700">
            API: {apiMode} {apiUrl ? ` · ${apiUrl}` : ""}. Ensure backend is running and .env.local is set (restart dev server after changing it).
          </p>
        </section>
      </div>
    );
  }

  const specialties = Array.from(
    new Set(cases.flatMap((c) => c.specialties || [])),
  );

  return (
    <div className="space-y-6">
      <section className="rounded-3xl border border-slate-200 bg-white/80 p-5 shadow-sm">
        <div className="flex items-center justify-between gap-2">
          <h1 className="text-xl font-semibold text-slate-900">
            Case library
          </h1>
          <span className="rounded-full bg-slate-200 px-2 py-0.5 text-[10px] font-medium text-slate-600" title={apiUrl || undefined}>
            API: {apiMode}
          </span>
        </div>
        <p className="mt-1 text-sm text-slate-600">
          Choose a real-data grounded case to simulate a focused emergency or
          internal medicine encounter.
        </p>
        <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-slate-600">
          <span className="rounded-full bg-emerald-50 px-2 py-0.5 font-medium text-emerald-700 ring-1 ring-emerald-100">
            {cases.length} available case
          </span>
          {specialties.map((s) => (
            <span
              key={s}
              className="rounded-full bg-slate-50 px-2 py-0.5 font-medium text-slate-700 ring-1 ring-slate-200"
            >
              {s}
            </span>
          ))}
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-2">
        {cases.map((c) => (
          <article
            key={c.case_id}
            className="flex flex-col justify-between rounded-3xl border border-slate-200 bg-white/90 p-4 shadow-sm transition hover:shadow-md"
          >
            <div className="space-y-2">
              <div className="flex items-center justify-between gap-2">
                <h2 className="text-sm font-semibold text-slate-900">
                  {c.presenting_complaint}
                </h2>
                <span className="rounded-full bg-slate-900 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-white">
                  {difficultyLabels[c.difficulty]}
                </span>
              </div>
              <p className="text-xs text-slate-600 line-clamp-3">
                {c.hpi || c.presenting_complaint}
              </p>
              {c.demographics.age > 0 && (
                <p className="text-xs text-slate-500">
                  {c.demographics.age}-year-old{" "}
                  {c.demographics.gender === "M" ? "male" : "female"}
                  {c.demographics.admission_type && c.demographics.admission_type !== "Unknown" && (
                    <> · Admission: {c.demographics.admission_type.toLowerCase()}</>
                  )}
                </p>
              )}
            </div>
            <div className="mt-3 flex items-center justify-between text-xs">
              <div className="flex flex-wrap gap-1">
                {c.specialties.slice(0, 2).map((s) => (
                  <span
                    key={s}
                    className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] text-slate-700"
                  >
                    {s}
                  </span>
                ))}
              </div>
              <Link
                href={`/session/${encodeURIComponent(c.case_id)}`}
                className="rounded-full bg-emerald-600 px-3 py-1 text-[11px] font-semibold text-white shadow-sm hover:bg-emerald-700"
              >
                Start case
              </Link>
            </div>
          </article>
        ))}
      </section>
    </div>
  );
}

