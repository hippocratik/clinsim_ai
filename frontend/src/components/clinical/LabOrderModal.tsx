"use client";

import { useState } from "react";
import { LAB_COSTS } from "@/lib/constants";

const LAB_CATEGORIES = {
  panels: [
    { id: "cbc", name: "Complete Blood Count", cost: LAB_COSTS.cbc },
    { id: "bmp", name: "Basic Metabolic Panel", cost: LAB_COSTS.bmp },
    { id: "cmp", name: "Comprehensive Metabolic Panel", cost: LAB_COSTS.cmp },
    { id: "cardiac", name: "Cardiac Enzymes", cost: LAB_COSTS.cardiac },
  ],
  individual: [
    { id: "troponin", name: "Troponin", cost: LAB_COSTS.troponin },
    { id: "bnp", name: "BNP", cost: LAB_COSTS.bnp },
    { id: "ddimer", name: "D-Dimer", cost: LAB_COSTS.ddimer },
    { id: "lactate", name: "Lactate", cost: LAB_COSTS.lactate },
  ],
};

interface LabOrderModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (labIds: string[]) => void;
}

export function LabOrderModal({
  isOpen,
  onClose,
  onConfirm,
}: LabOrderModalProps) {
  const [selected, setSelected] = useState<Set<string>>(new Set());

  if (!isOpen) return null;

  const handleClose = () => {
    setSelected(new Set());
    onClose();
  };

  const toggle = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const totalCost = Array.from(selected).reduce((sum, id) => {
    const cost = LAB_COSTS[id] ?? 1;
    return sum + cost;
  }, 0);

  const handleConfirm = () => {
    if (selected.size === 0) return;
    onConfirm(Array.from(selected));
    setSelected(new Set());
    onClose();
  };

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/40 px-4">
      <div className="w-full max-w-md rounded-3xl bg-white p-5 shadow-xl">
        <header className="mb-3 flex items-center justify-between">
          <div>
            <h2 className="text-sm font-semibold text-slate-900">
              Order labs & tests
            </h2>
            <p className="mt-0.5 text-xs text-slate-500">
              Choose focused tests that will meaningfully change your
              management.
            </p>
          </div>
          <button
            type="button"
            onClick={handleClose}
            className="rounded-full px-2 py-1 text-xs text-slate-500 hover:bg-slate-100"
          >
            Esc
          </button>
        </header>

        <div className="space-y-4 text-sm">
          <div>
            <h3 className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">
              Panels
            </h3>
            <div className="mt-2 space-y-1.5">
              {LAB_CATEGORIES.panels.map((lab) => (
                <button
                  key={lab.id}
                  type="button"
                  onClick={() => toggle(lab.id)}
                  className={`flex w-full items-center justify-between rounded-2xl border px-3 py-2 text-left text-xs ${
                    selected.has(lab.id)
                      ? "border-blue-500 bg-blue-50 text-blue-900"
                      : "border-slate-200 bg-slate-50 text-slate-800 hover:bg-slate-100"
                  }`}
                >
                  <span>{lab.name}</span>
                  <span className="text-[11px] font-semibold text-slate-700">
                    −{lab.cost}
                  </span>
                </button>
              ))}
            </div>
          </div>

          <div>
            <h3 className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">
              Individual tests
            </h3>
            <div className="mt-2 flex flex-wrap gap-1.5">
              {LAB_CATEGORIES.individual.map((lab) => (
                <button
                  key={lab.id}
                  type="button"
                  onClick={() => toggle(lab.id)}
                  className={`rounded-full px-3 py-1 text-[11px] ${
                    selected.has(lab.id)
                      ? "bg-blue-600 text-white"
                      : "bg-slate-100 text-slate-800 hover:bg-slate-200"
                  }`}
                >
                  {lab.name} · −{lab.cost}
                </button>
              ))}
            </div>
          </div>
        </div>

        <footer className="mt-4 flex items-center justify-between border-t border-slate-100 pt-3 text-xs">
          <span className="text-slate-600">
            Estimated cost:{" "}
            <span className="font-semibold text-slate-900">
              −{totalCost} points
            </span>
          </span>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={handleClose}
              className="rounded-2xl bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 ring-1 ring-slate-200 hover:bg-slate-50"
            >
              Cancel
            </button>
            <button
              type="button"
              disabled={selected.size === 0}
              onClick={handleConfirm}
              className="rounded-2xl bg-emerald-600 px-3 py-1.5 text-xs font-semibold text-white shadow-sm hover:bg-emerald-700 disabled:cursor-not-allowed disabled:bg-emerald-300"
            >
              Order selected
            </button>
          </div>
        </footer>
      </div>
    </div>
  );
}

