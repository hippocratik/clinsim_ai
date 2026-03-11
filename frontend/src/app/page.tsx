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

const difficultyStyles: Record<Difficulty, string> = {
  easy: "bg-emerald-100 text-emerald-800 ring-1 ring-emerald-200",
  medium: "bg-amber-100 text-amber-800 ring-1 ring-amber-200",
  hard: "bg-rose-100 text-rose-800 ring-1 ring-rose-200",
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
        <section className="rounded-3xl border border-rose-200 bg-rose-50 p-6">
          <h1 className="text-2xl font-bold text-rose-900">Case library</h1>
          <p className="mt-2 text-base text-rose-800">
            Could not load cases: {message}
          </p>
          <p className="mt-1 text-sm text-rose-700">
            API: {apiMode}
            {apiUrl ? ` · ${apiUrl}` : ""}. Ensure backend is running and
            .env.local is set (restart dev server after changing it).
          </p>
        </section>
      </div>
    );
  }

  const specialties = Array.from(
    new Set(cases.flatMap((c) => c.specialties || [])),
  );

  return (
    <div className="space-y-8">
      {/* ── Hero header ── */}
      <section className="rounded-3xl border border-slate-200 bg-white/90 px-8 py-10 shadow-sm">
        <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
          <div>
            <h1 className="text-4xl font-bold tracking-tight text-slate-900">
              Case library
            </h1>
            <p className="mt-3 max-w-2xl text-lg text-slate-600">
              Choose a real-data grounded case to simulate a focused emergency
              or internal medicine encounter.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <span className="rounded-full bg-emerald-50 px-3 py-1 text-sm font-semibold text-emerald-700 ring-1 ring-emerald-100">
              {cases.length} available {cases.length === 1 ? "case" : "cases"}
            </span>
            {specialties.map((s) => (
              <span
                key={s}
                className="rounded-full bg-slate-50 px-3 py-1 text-sm font-medium text-slate-700 ring-1 ring-slate-200"
              >
                {s}
              </span>
            ))}
            <span
              className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-500"
              title={apiUrl || undefined}
            >
              API: {apiMode}
            </span>
          </div>
        </div>
      </section>

      {/* ── Case grid ── */}
      <section className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
        {cases.map((c) => (
          <article
            key={c.case_id}
            className="flex flex-col justify-between rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-sm transition hover:shadow-md"
          >
            <div className="space-y-3">
              {/* Title + difficulty */}
              <div className="flex items-start justify-between gap-3">
                <h2 className="text-lg font-semibold leading-snug text-slate-900">
                  {c.presenting_complaint}
                </h2>
                <span
                  className={`mt-0.5 shrink-0 rounded-full px-3 py-0.5 text-xs font-bold uppercase tracking-wide ${difficultyStyles[c.difficulty]}`}
                >
                  {difficultyLabels[c.difficulty]}
                </span>
              </div>

              {/* HPI */}
              <p className="text-sm leading-relaxed text-slate-600 line-clamp-3">
                {c.hpi || c.presenting_complaint}
              </p>

              {/* Demographics */}
              {c.demographics.age > 0 && (
                <p className="text-sm text-slate-500">
                  {c.demographics.age}-year-old{" "}
                  {c.demographics.gender === "M" ? "male" : "female"}
                  {c.demographics.admission_type &&
                    c.demographics.admission_type !== "Unknown" && (
                      <> · Admission: {c.demographics.admission_type.toLowerCase()}</>
                    )}
                </p>
              )}
            </div>

            {/* Footer */}
            <div className="mt-5 flex items-center justify-between">
              <div className="flex flex-wrap gap-1.5">
                {c.specialties.slice(0, 2).map((s) => (
                  <span
                    key={s}
                    className="rounded-full bg-slate-100 px-3 py-0.5 text-xs font-medium text-slate-700"
                  >
                    {s}
                  </span>
                ))}
              </div>
              <Link
                href={`/session/${encodeURIComponent(c.case_id)}`}
                className="rounded-full bg-emerald-600 px-4 py-1.5 text-sm font-semibold text-white shadow-sm hover:bg-emerald-700"
              >
                Start case →
              </Link>
            </div>
          </article>
        ))}
      </section>
    </div>
  );
}