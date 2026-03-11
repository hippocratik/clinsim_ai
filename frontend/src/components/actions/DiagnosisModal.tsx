"use client";

import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import type { Diagnosis, DiagnoseRequest } from "@/lib/types";

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
  const [query, setQuery] = useState("");
  const [primary, setPrimary] = useState<Diagnosis | null>(null);
  const [diffs, setDiffs] = useState<Diagnosis[]>([]);
  const [reasoning, setReasoning] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [searchResults, setSearchResults] = useState<Diagnosis[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);

  useEffect(() => {
    const q = query.trim();
    if (!q) {
      setSearchResults([]);
      setSearchError(null);
      return;
    }

    let cancelled = false;
    setIsSearching(true);
    setSearchError(null);

    const handle = window.setTimeout(async () => {
      try {
        const results = await api.searchDiagnoses(q);
        if (cancelled) return;
        setSearchResults(results);
      } catch (err) {
        if (cancelled) return;
        setSearchResults([]);
        setSearchError(
          err instanceof Error
            ? err.message
            : "Failed to search diagnoses",
        );
      } finally {
        if (!cancelled) {
          setIsSearching(false);
        }
      }
    }, 250);

    return () => {
      cancelled = true;
      window.clearTimeout(handle);
    };
  }, [query]);

  const filteredOptions = useMemo(() => {
    // 优先使用后端搜索结果，其次是病例内诊断，最后是兜底选项。
    const base: Diagnosis[] =
      searchResults.length > 0
        ? searchResults
        : caseDiagnoses.length > 0
          ? caseDiagnoses
          : [
              {
                icd9_code: "000.00",
                description: "Unspecified diagnosis",
                is_primary: true,
              },
            ];
    const q = query.toLowerCase().trim();
    if (!q || searchResults.length > 0) {
      // 当有后端搜索结果时，已经是带过滤的结果，直接返回。
      return base;
    }
    return base.filter(
      (opt) =>
        opt.icd9_code.toLowerCase().includes(q) ||
        opt.description.toLowerCase().includes(q),
    );
  }, [caseDiagnoses, query, searchResults]);

  if (!isOpen) return null;

  const toggleDiff = (diag: Diagnosis) => {
    setDiffs((prev) => {
      const exists = prev.find((d) => d.icd9_code === diag.icd9_code);
      if (exists) {
        return prev.filter((d) => d.icd9_code !== diag.icd9_code);
      }
      if (prev.length >= 3) return prev;
      return [...prev, { ...diag, is_primary: false }];
    });
  };

  const handleSubmit = async () => {
    if (!primary) return;
    setIsSubmitting(true);
    try {
      await onSubmit({
        primaryDiagnosis: { ...primary, is_primary: true },
        differentials: diffs.map((d) => ({ ...d, is_primary: false })),
        reasoning: reasoning || undefined,
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/40 px-4">
      <div className="flex max-h-[90vh] w-full max-w-lg flex-col rounded-3xl bg-white p-5 shadow-xl">
        <header className="mb-3 flex-shrink-0 space-y-1">
          <h2 className="text-sm font-semibold text-slate-900">
            Submit diagnosis
          </h2>
          <p className="text-xs text-slate-500">
            Choose a primary ICD-9 diagnosis and optionally up to three
            differentials.{" "}
          </p>
        </header>

        <div className="min-h-0 flex-1 space-y-4 overflow-y-auto text-sm">
          {caseDiagnoses.length === 0 && searchResults.length === 0 && (
            <p className="rounded-2xl border border-amber-100 bg-amber-50 px-3 py-2 text-xs text-amber-800">
              Case diagnosis list not available. Search by ICD-9 code or
              description below, or type a code to select.
            </p>
          )}
          <div>
            <label className="block text-xs font-medium text-slate-700">
              Search ICD-9
            </label>
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Type code or description…"
              className="mt-1 w-full rounded-2xl border border-slate-200 bg-white px-3 py-2 text-sm outline-none ring-blue-200 focus:border-blue-500 focus:ring-2"
            />
            {isSearching && (
              <p className="mt-1 text-[11px] text-slate-500">
                Searching diagnoses…
              </p>
            )}
            {searchError && (
              <p className="mt-1 text-[11px] text-rose-600">
                {searchError}
              </p>
            )}
            <div className="mt-2 max-h-32 space-y-1 overflow-y-auto rounded-2xl border border-slate-100 bg-slate-50 p-1.5 text-xs">
              {filteredOptions.map((opt) => (
                <button
                  key={opt.icd9_code}
                  type="button"
                  onClick={() => setPrimary(opt)}
                  className={`flex w-full items-center justify-between rounded-xl px-2.5 py-1.5 text-left ${
                    primary?.icd9_code === opt.icd9_code
                      ? "bg-blue-600 text-white"
                      : "bg-white text-slate-800 hover:bg-slate-100"
                  }`}
                >
                  <span>
                    <span className="font-mono text-[11px]">
                      {opt.icd9_code}
                    </span>{" "}
                    · {opt.description}
                  </span>
                  {primary?.icd9_code === opt.icd9_code && (
                    <span className="ml-2 text-[10px] font-semibold">
                      Primary
                    </span>
                  )}
                </button>
              ))}
            </div>
          </div>

          <div>
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-slate-700">
                Differential diagnoses (optional, up to 3)
              </span>
              <span className="text-[10px] text-slate-500">
                {diffs.length}/3 selected
              </span>
            </div>
            <div className="mt-1 flex flex-wrap gap-1.5">
              {filteredOptions.map((opt) => (
                <button
                  key={`diff-${opt.icd9_code}`}
                  type="button"
                  onClick={() => toggleDiff(opt)}
                  className={`rounded-full px-3 py-1 text-[11px] ${
                    diffs.some((d) => d.icd9_code === opt.icd9_code)
                      ? "bg-amber-500 text-white"
                      : "bg-slate-100 text-slate-800 hover:bg-slate-200"
                  }`}
                >
                  {opt.icd9_code} · {opt.description}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-700">
              Clinical reasoning (optional)
            </label>
            <textarea
              value={reasoning}
              onChange={(e) => setReasoning(e.target.value)}
              rows={3}
              placeholder="Summarize your key findings and why they support your diagnosis."
              className="mt-1 w-full rounded-2xl border border-slate-200 bg-white px-3 py-2 text-xs outline-none ring-blue-200 focus:border-blue-500 focus:ring-2"
            />
          </div>
        </div>

        <footer className="mt-4 flex-shrink-0 border-t border-slate-100 pt-3 text-xs">
          {(primary || diffs.length > 0) && (
            <div className="mb-3 max-h-20 overflow-y-auto">
              <div className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-slate-500">
                Selected
              </div>
              <div className="flex flex-wrap gap-1.5">
                {primary && (
                  <button
                    type="button"
                    onClick={() => setPrimary(null)}
                    className="inline-flex items-center gap-1 rounded-full bg-blue-100 pl-2 pr-1 py-0.5 text-[11px] font-medium text-blue-800 hover:bg-blue-200"
                  >
                    <span>
                      Primary: {primary.icd9_code} · {primary.description}
                    </span>
                    <span className="rounded-full px-1 text-[9px] leading-none">
                      ×
                    </span>
                  </button>
                )}
                {diffs.map((d) => (
                  <button
                    key={d.icd9_code}
                    type="button"
                    onClick={() =>
                      setDiffs((prev) =>
                        prev.filter((x) => x.icd9_code !== d.icd9_code),
                      )
                    }
                    className="inline-flex items-center gap-1 rounded-full bg-slate-100 pl-2 pr-1 py-0.5 text-[11px] text-slate-700 hover:bg-slate-200"
                  >
                    <span>
                      Diff: {d.icd9_code} · {d.description}
                    </span>
                    <span className="rounded-full px-1 text-[9px] leading-none">
                      ×
                    </span>
                  </button>
                ))}
              </div>
            </div>
          )}
          <div className="flex items-center justify-between">
            <div className="max-w-xs text-slate-600">
              <p>
                Submitting will lock in your decisions and show the scoring
                breakdown.
              </p>
              {showConfirm && (
                <p className="mt-1 font-semibold text-rose-600">
                  Are you sure you want to submit? You will not be able to change
                  your diagnosis.
                </p>
              )}
            </div>
            <div className="flex gap-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded-2xl bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 ring-1 ring-slate-200 hover:bg-slate-50"
            >
              Cancel
            </button>
            {showConfirm ? (
              <>
                <button
                  type="button"
                  disabled={isSubmitting}
                  onClick={() => setShowConfirm(false)}
                  className="rounded-2xl bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 ring-1 ring-slate-200 hover:bg-slate-50"
                >
                  Go back
                </button>
                <button
                  type="button"
                  disabled={!primary || isSubmitting}
                  onClick={() => void handleSubmit()}
                  className="rounded-2xl bg-emerald-600 px-3 py-1.5 text-xs font-semibold text-white shadow-sm hover:bg-emerald-700 disabled:cursor-not-allowed disabled:bg-emerald-300"
                >
                  {isSubmitting ? "Submitting…" : "Confirm submit"}
                </button>
              </>
            ) : (
              <button
                type="button"
                disabled={!primary}
                onClick={() => setShowConfirm(true)}
                className="rounded-2xl bg-emerald-600 px-3 py-1.5 text-xs font-semibold text-white shadow-sm hover:bg-emerald-700 disabled:cursor-not-allowed disabled:bg-emerald-300"
              >
                Review & submit
              </button>
            )}
            </div>
          </div>
        </footer>
      </div>
    </div>
  );
}

