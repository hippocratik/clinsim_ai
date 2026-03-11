"use client";

import { useState, useMemo } from "react";
import { LAB_COSTS } from "@/lib/constants";
import {
  LABS_BY_CATEGORY,
  type LabItem,
  type LabCategory,
} from "@/lib/labs-data";

interface LabOrderModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (labIds: string[]) => void;
}

const CATEGORY_ORDER: LabCategory[] = [
  "Hematology",
  "Blood Gas",
  "Chemistry",
];

function labMatchesSearch(lab: LabItem, query: string): boolean {
  if (!query.trim()) return true;
  const q = query.toLowerCase().trim();
  return (
    lab.lab_name.toLowerCase().includes(q) ||
    lab.fluid.toLowerCase().includes(q) ||
    lab.itemid.includes(q)
  );
}

function getLabDisplayLabel(lab: LabItem): string {
  if (lab.fluid === "Blood" || lab.fluid === "BLOOD") {
    return lab.lab_name;
  }
  return `${lab.lab_name} (${lab.fluid})`;
}

export function LabOrderModal({
  isOpen,
  onClose,
  onConfirm,
}: LabOrderModalProps) {
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [searchQuery, setSearchQuery] = useState("");
  const [expandedCategories, setExpandedCategories] = useState<
    Set<LabCategory>
  >(new Set());

  const handleClose = () => {
    setSelected(new Set());
    setSearchQuery("");
    onClose();
  };

  const toggle = (itemid: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      const key = itemid;
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  const isSelected = (itemid: string) => selected.has(itemid);

  const filteredByCategory = useMemo(() => {
    const result: Partial<Record<LabCategory, LabItem[]>> = {};
    for (const cat of CATEGORY_ORDER) {
      const labs = LABS_BY_CATEGORY[cat] ?? [];
      const filtered = labs.filter((lab) => labMatchesSearch(lab, searchQuery));
      if (filtered.length > 0) {
        result[cat] = filtered;
      }
    }
    return result;
  }, [searchQuery]);

  const selectedLabsForConfirm = useMemo(() => {
    const names: string[] = [];
    for (const key of selected) {
      for (const cat of CATEGORY_ORDER) {
        const lab = (LABS_BY_CATEGORY[cat] ?? []).find((l) => l.itemid === key);
        if (lab) {
          names.push(lab.lab_name);
          break;
        }
      }
    }
    return names;
  }, [selected]);

  const selectedLabsWithIds = useMemo(() => {
    const items: { itemid: string; label: string }[] = [];
    for (const key of selected) {
      for (const cat of CATEGORY_ORDER) {
        const lab = (LABS_BY_CATEGORY[cat] ?? []).find((l) => l.itemid === key);
        if (lab) {
          items.push({ itemid: key, label: getLabDisplayLabel(lab) });
          break;
        }
      }
    }
    return items;
  }, [selected]);

  const totalCost = Array.from(selected).reduce((sum, itemid) => {
    let lab: LabItem | undefined;
    for (const cat of CATEGORY_ORDER) {
      lab = (LABS_BY_CATEGORY[cat] ?? []).find((l) => l.itemid === itemid);
      if (lab) break;
    }
    const key = lab?.lab_name?.toLowerCase() ?? "";
    const cost = LAB_COSTS[key] ?? 1;
    return sum + cost;
  }, 0);

  const handleConfirm = () => {
    if (selectedLabsForConfirm.length === 0) return;
    onConfirm(selectedLabsForConfirm);
    setSelected(new Set());
    setSearchQuery("");
    onClose();
  };

  const hasResults = Object.keys(filteredByCategory).length > 0;

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/40 px-4">
      <div className="flex max-h-[90vh] w-full max-w-md flex-col rounded-3xl bg-white shadow-xl">
        <header className="flex-shrink-0 p-5 pb-0">
          <div className="mb-3 flex items-center justify-between">
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
          </div>
          <div className="relative">
            <input
              type="search"
              placeholder="Search by name, fluid, or ID…"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-3 py-2 pr-9 text-xs text-slate-800 placeholder:text-slate-400 focus:border-blue-300 focus:bg-white focus:outline-none focus:ring-1 focus:ring-blue-200"
            />
            {searchQuery && (
              <button
                type="button"
                onClick={() => setSearchQuery("")}
                className="absolute right-2 top-1/2 -translate-y-1/2 rounded p-1 text-slate-400 hover:bg-slate-200 hover:text-slate-600"
              >
                <span className="sr-only">Clear</span>
                ×
              </button>
            )}
          </div>
        </header>

        <div className="min-h-0 flex-1 space-y-3 overflow-y-auto p-5 pt-3 text-sm">
          {hasResults ? (
            CATEGORY_ORDER.map((category) => {
              const labs = filteredByCategory[category];
              if (!labs || labs.length === 0) return null;

              const isExpanded = expandedCategories.has(category);
              const count = labs.length;

              return (
                <div key={category} className="rounded-2xl border border-slate-200 bg-slate-50">
                  <button
                    type="button"
                    onClick={() => {
                      setExpandedCategories((prev) => {
                        const next = new Set(prev);
                        if (next.has(category)) next.delete(category);
                        else next.add(category);
                        return next;
                      });
                    }}
                    className="flex w-full items-center justify-between px-3 py-2 text-left"
                  >
                    <div>
                      <h3 className="text-[11px] font-semibold uppercase tracking-wide text-slate-600">
                        {category}
                      </h3>
                      <p className="mt-0.5 text-[11px] text-slate-500">
                        {count} labs
                      </p>
                    </div>
                    <span className="text-xs text-slate-500">
                      {isExpanded ? "−" : "+"}
                    </span>
                  </button>

                  {isExpanded && (
                    <div className="border-t border-slate-200 bg-white/60 px-3 py-2">
                      <div className="space-y-1.5">
                        {labs.map((lab) => {
                          const id = lab.itemid;
                          const label = getLabDisplayLabel(lab);
                          const key = lab.lab_name.toLowerCase();
                          const cost = LAB_COSTS[key] ?? 1;
                          return (
                            <button
                              key={id}
                              type="button"
                              onClick={() => toggle(id)}
                              className={`flex w-full items-center justify-between rounded-2xl border px-3 py-2 text-left text-xs ${
                                isSelected(id)
                                  ? "border-blue-500 bg-blue-50 text-blue-900"
                                  : "border-slate-200 bg-slate-50 text-slate-800 hover:bg-slate-100"
                              }`}
                            >
                              <span>{label}</span>
                              <span className="text-[11px] font-semibold text-slate-700">
                                −{cost}
                              </span>
                            </button>
                          );
                        })}
                      </div>
                    </div>
                  )}
                </div>
              );
            })
          ) : (
            <p className="rounded-2xl border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-600">
              No labs match &quot;{searchQuery}&quot;
            </p>
          )}
        </div>

        <footer className="flex-shrink-0 border-t border-slate-100 p-4 pt-3 text-xs">
          {selectedLabsWithIds.length > 0 && (
            <div className="mb-2 max-h-20 overflow-y-auto">
              <div className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-slate-500">
                Selected labs ({selectedLabsWithIds.length})
              </div>
              <div className="flex flex-wrap gap-1.5">
                {selectedLabsWithIds.map(({ itemid, label }) => (
                  <button
                    key={itemid}
                    type="button"
                    onClick={() => {
                      setSelected((prev) => {
                        const next = new Set(prev);
                        next.delete(itemid);
                        return next;
                      });
                    }}
                    className="inline-flex items-center gap-1 rounded-full bg-slate-100 pl-2 pr-1 py-0.5 text-[11px] text-slate-700 hover:bg-slate-200"
                  >
                    <span>{label}</span>
                    <span className="rounded-full px-1 text-[9px] leading-none">
                      ×
                    </span>
                  </button>
                ))}
              </div>
            </div>
          )}
          <div className="flex items-center justify-between">
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
          </div>
        </footer>
      </div>
    </div>
  );
}
