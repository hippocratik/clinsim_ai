"use client";

import { useState } from "react";

interface LabOrderModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (labIds: string[]) => Promise<void>;
}

const PANELS = [
  { id: "cbc",     label: "Complete Blood Count",      cost: 2, desc: "WBC, RBC, Hgb, Hct, Plt" },
  { id: "bmp",     label: "Basic Metabolic Panel",     cost: 3, desc: "Na, K, Cl, CO₂, BUN, Cr, Glucose" },
  { id: "cmp",     label: "Comprehensive Metabolic Panel", cost: 4, desc: "BMP + LFTs, albumin, total protein" },
  { id: "cardiac", label: "Cardiac Enzymes",           cost: 3, desc: "Troponin, CK-MB, myoglobin" },
];

const INDIVIDUAL = [
  { id: "troponin", label: "Troponin",  cost: 2 },
  { id: "bnp",      label: "BNP",       cost: 2 },
  { id: "ddimer",   label: "D-Dimer",   cost: 2 },
  { id: "lactate",  label: "Lactate",   cost: 1 },
  { id: "abg",      label: "ABG",       cost: 2 },
  { id: "lipase",   label: "Lipase",    cost: 1 },
  { id: "ua",       label: "Urinalysis",cost: 1 },
  { id: "ptt",      label: "PT/PTT/INR",cost: 2 },
];

export function LabOrderModal({ isOpen, onClose, onConfirm }: LabOrderModalProps) {
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [isOrdering, setIsOrdering] = useState(false);

  if (!isOpen) return null;

  const toggle = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  const totalCost = [...selected].reduce((acc, id) => {
    const p = PANELS.find((x) => x.id === id);
    const i = INDIVIDUAL.find((x) => x.id === id);
    return acc + (p?.cost ?? i?.cost ?? 0);
  }, 0);

  const handleConfirm = async () => {
    if (selected.size === 0) return;
    setIsOrdering(true);
    await onConfirm([...selected]);
    setSelected(new Set());
    setIsOrdering(false);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
      <div className="relative w-full max-w-2xl rounded-3xl bg-white shadow-2xl">

        {/* Header */}
        <div className="border-b border-slate-100 px-8 py-6">
          <div className="flex items-start justify-between">
            <div>
              <h2 className="text-2xl font-bold text-slate-900">Order labs & tests</h2>
              <p className="mt-1.5 text-base text-slate-500">
                Choose focused tests that will meaningfully change your management.
              </p>
            </div>
            <button
              type="button"
              onClick={onClose}
              className="ml-4 rounded-xl border border-slate-200 px-3 py-1.5 text-sm font-semibold text-slate-500 hover:bg-slate-50"
            >
              Esc
            </button>
          </div>
        </div>

        {/* Body */}
        <div className="max-h-[60vh] overflow-y-auto px-8 py-6 space-y-7">

          {/* Panels */}
          <section>
            <p className="mb-3 text-xs font-bold uppercase tracking-widest text-slate-400">Panels</p>
            <div className="space-y-2.5">
              {PANELS.map((p) => {
                const isSelected = selected.has(p.id);
                return (
                  <button
                    key={p.id}
                    type="button"
                    onClick={() => toggle(p.id)}
                    className={`flex w-full items-center justify-between rounded-2xl border px-5 py-4 text-left transition ${
                      isSelected
                        ? "border-emerald-400 bg-emerald-50 ring-2 ring-emerald-200"
                        : "border-slate-200 bg-slate-50 hover:border-slate-300 hover:bg-white"
                    }`}
                  >
                    <div>
                      <p className={`text-lg font-semibold ${isSelected ? "text-emerald-800" : "text-slate-800"}`}>
                        {p.label}
                      </p>
                      <p className="mt-0.5 text-sm text-slate-500">{p.desc}</p>
                    </div>
                    <span className={`ml-4 shrink-0 text-lg font-bold ${isSelected ? "text-emerald-700" : "text-slate-500"}`}>
                      −{p.cost}
                    </span>
                  </button>
                );
              })}
            </div>
          </section>

          {/* Individual */}
          <section>
            <p className="mb-3 text-xs font-bold uppercase tracking-widest text-slate-400">Individual Tests</p>
            <div className="flex flex-wrap gap-3">
              {INDIVIDUAL.map((t) => {
                const isSelected = selected.has(t.id);
                return (
                  <button
                    key={t.id}
                    type="button"
                    onClick={() => toggle(t.id)}
                    className={`rounded-2xl border px-5 py-3 text-base font-semibold transition ${
                      isSelected
                        ? "border-emerald-400 bg-emerald-50 text-emerald-800 ring-2 ring-emerald-200"
                        : "border-slate-200 bg-slate-50 text-slate-700 hover:border-slate-300 hover:bg-white"
                    }`}
                  >
                    {t.label}
                    <span className="ml-2 font-normal text-slate-400">· −{t.cost}</span>
                  </button>
                );
              })}
            </div>
          </section>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between border-t border-slate-100 px-8 py-5">
          <p className="text-base text-slate-600">
            Estimated cost:{" "}
            <span className="font-bold text-slate-900">−{totalCost} points</span>
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
              onClick={() => void handleConfirm()}
              disabled={selected.size === 0 || isOrdering}
              className="rounded-2xl bg-emerald-600 px-6 py-3 text-base font-bold text-white shadow-sm transition hover:bg-emerald-700 disabled:opacity-40"
            >
              {isOrdering ? "Ordering…" : `Order selected (${selected.size})`}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}