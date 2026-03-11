"use client";

import { useState } from "react";
import type { DiagnoseRequest, Diagnosis } from "@/lib/types";

interface DiagnosisModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (payload: DiagnoseRequest) => Promise<void>;
  caseDiagnoses: Diagnosis[];
}

export function DiagnosisModal({
  isOpen,
  onClose,
  onSubmit,
  caseDiagnoses,
}: DiagnosisModalProps) {
  const [search, setSearch] = useState("");
  const [primary, setPrimary] = useState<Diagnosis | null>(null);
  const [differentials, setDifferentials] = useState<Diagnosis[]>([]);
  const [reasoning, setReasoning] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!isOpen) return null;

  // Build candidate list from caseDiagnoses + fallback
  const defaultOption: Diagnosis = {
    icd9_code: "000.00",
    description: "Unspecified diagnosis",
    is_primary: false,
  };

  const candidates: Diagnosis[] = caseDiagnoses.length > 0
    ? caseDiagnoses
    : [defaultOption];

  const filtered = candidates.filter(
    (d) =>
      d.description.toLowerCase().includes(search.toLowerCase()) ||
      d.icd9_code.includes(search),
  );

  const noCaseList = caseDiagnoses.length === 0;

  const toggleDifferential = (d: Diagnosis) => {
    setDifferentials((prev) => {
      const exists = prev.find((x) => x.icd9_code === d.icd9_code);
      if (exists) return prev.filter((x) => x.icd9_code !== d.icd9_code);
      if (prev.length >= 3) return prev;
      return [...prev, { ...d, is_primary: false }];
    });
  };

  const handleSubmit = async () => {
    if (!primary) return;
    setIsSubmitting(true);
    await onSubmit({
      primaryDiagnosis: { ...primary, is_primary: true },
      differentials,
      reasoning: reasoning.trim() || undefined,
    });
    setIsSubmitting(false);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
      <div className="relative w-full max-w-xl rounded-3xl bg-white shadow-2xl">

        {/* Header */}
        <div className="border-b border-slate-100 px-8 py-6">
          <h2 className="text-2xl font-bold text-slate-900">Submit diagnosis</h2>
          <p className="mt-1.5 text-base text-slate-500">
            Choose a primary ICD-9 diagnosis and optionally up to three differentials.
          </p>
        </div>

        {/* Body */}
        <div className="max-h-[65vh] overflow-y-auto px-8 py-6 space-y-6">

          {/* Case list warning */}
          {noCaseList && (
            <div className="rounded-2xl border border-amber-200 bg-amber-50 px-5 py-4 text-base text-amber-800">
              Case diagnosis list not available. Search by ICD-9 code or description below, or type a code to select.
            </div>
          )}

          {/* Search */}
          <div>
            <label className="mb-2 block text-base font-bold text-slate-700">
              Search ICD-9
            </label>
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Type code or description…"
              className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-5 py-3.5 text-base outline-none placeholder:text-slate-400 focus:border-emerald-400 focus:ring-2 focus:ring-emerald-100"
            />

            {/* Results list */}
            {search.length > 0 && (
              <div className="mt-2 space-y-1.5 max-h-48 overflow-y-auto">
                {filtered.length === 0 ? (
                  <p className="px-1 text-sm text-slate-400">No matches found.</p>
                ) : (
                  filtered.map((d) => (
                    <button
                      key={d.icd9_code}
                      type="button"
                      onClick={() => { setPrimary(d); setSearch(""); }}
                      className={`flex w-full items-center gap-3 rounded-xl px-4 py-3 text-left text-base transition hover:bg-emerald-50 ${
                        primary?.icd9_code === d.icd9_code ? "bg-emerald-50 font-semibold text-emerald-800" : "text-slate-800"
                      }`}
                    >
                      <span className="shrink-0 rounded-lg bg-slate-100 px-2 py-1 font-mono text-sm text-slate-600">
                        {d.icd9_code}
                      </span>
                      {d.description}
                    </button>
                  ))
                )}
              </div>
            )}

            {/* Selected primary */}
            {primary && search.length === 0 && (
              <div className="mt-3 flex items-center gap-3 rounded-2xl border border-emerald-200 bg-emerald-50 px-5 py-3.5">
                <span className="rounded-lg bg-emerald-100 px-2 py-1 font-mono text-sm text-emerald-700">
                  {primary.icd9_code}
                </span>
                <span className="flex-1 text-base font-semibold text-emerald-900">{primary.description}</span>
                <button
                  type="button"
                  onClick={() => setPrimary(null)}
                  className="text-sm text-slate-400 hover:text-slate-600"
                >
                  ✕
                </button>
              </div>
            )}

            {!primary && search.length === 0 && (
              <div
                className="mt-3 flex cursor-pointer items-center gap-3 rounded-2xl border border-slate-200 bg-slate-50 px-5 py-3.5 hover:bg-white"
                onClick={() => setPrimary(defaultOption)}
              >
                <span className="rounded-lg bg-slate-100 px-2 py-1 font-mono text-sm text-slate-600">
                  {defaultOption.icd9_code}
                </span>
                <span className="text-base text-slate-500">{defaultOption.description}</span>
              </div>
            )}
          </div>

          {/* Differentials */}
          <div>
            <div className="mb-2 flex items-center justify-between">
              <label className="text-base font-bold text-slate-700">
                Differential diagnoses <span className="font-normal text-slate-400">(optional, up to 3)</span>
              </label>
              <span className="text-sm font-semibold text-slate-400">{differentials.length}/3 selected</span>
            </div>
            <div className="flex flex-wrap gap-2">
              {candidates.slice(0, 6).map((d) => {
                const isOn = differentials.some((x) => x.icd9_code === d.icd9_code);
                const isPrimary = primary?.icd9_code === d.icd9_code;
                return (
                  <button
                    key={d.icd9_code}
                    type="button"
                    disabled={isPrimary || (!isOn && differentials.length >= 3)}
                    onClick={() => toggleDifferential(d)}
                    className={`rounded-2xl border px-4 py-2.5 text-sm font-medium transition ${
                      isOn
                        ? "border-blue-300 bg-blue-50 text-blue-800"
                        : isPrimary
                          ? "cursor-not-allowed border-slate-200 bg-slate-100 text-slate-400"
                          : "border-slate-200 bg-slate-50 text-slate-700 hover:bg-white"
                    }`}
                  >
                    <span className="font-mono text-xs text-slate-400 mr-1.5">{d.icd9_code}</span>
                    {d.description}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Reasoning */}
          <div>
            <label className="mb-2 block text-base font-bold text-slate-700">
              Clinical reasoning <span className="font-normal text-slate-400">(optional)</span>
            </label>
            <textarea
              value={reasoning}
              onChange={(e) => setReasoning(e.target.value)}
              rows={4}
              placeholder="Summarize your key findings and why they support your diagnosis."
              className="w-full resize-none rounded-2xl border border-slate-200 bg-slate-50 px-5 py-4 text-base outline-none placeholder:text-slate-400 focus:border-emerald-400 focus:ring-2 focus:ring-emerald-100"
            />
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between border-t border-slate-100 px-8 py-5">
          <p className="max-w-[55%] text-sm text-slate-500">
            Submitting will lock in your decisions and show the scoring breakdown.
          </p>
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={onClose}
              className="rounded-2xl border border-slate-200 px-6 py-3 text-base font-semibold text-slate-700 hover:bg-slate-50"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={() => void handleSubmit()}
              disabled={!primary || isSubmitting}
              className="rounded-2xl bg-emerald-600 px-6 py-3 text-base font-bold text-white shadow-sm transition hover:bg-emerald-700 disabled:opacity-40"
            >
              {isSubmitting ? "Submitting…" : "Review & submit"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}