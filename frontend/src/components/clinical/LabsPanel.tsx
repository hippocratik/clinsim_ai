import type { OrderedLab } from "@/lib/types";

interface LabsPanelProps {
  orderedLabs: OrderedLab[];
  resourcesUsed: number;
  maxResources: number;
  onOpenOrderModal: () => void;
}

const flagStyles: Record<string, string> = {
  critical: "bg-rose-50 text-rose-700 ring-1 ring-rose-200",
  high:     "bg-amber-50 text-amber-700 ring-1 ring-amber-200",
  low:      "bg-blue-50 text-blue-700 ring-1 ring-blue-200",
  normal:   "bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200",
};

const flagLabels: Record<string, string> = {
  critical: "CRIT",
  high:     "HIGH",
  low:      "LOW",
  normal:   "NL",
};

export function LabsPanel({
  orderedLabs,
  resourcesUsed,
  maxResources,
  onOpenOrderModal,
}: LabsPanelProps) {
  const remaining = Math.max(maxResources - resourcesUsed, 0);
  const pct = Math.min(Math.round((resourcesUsed / maxResources) * 100), 100);
  const barColor = pct > 75 ? "bg-rose-500" : pct > 40 ? "bg-amber-500" : "bg-emerald-500";

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="mb-5 flex items-center justify-between">
        <h3 className="text-base font-bold uppercase tracking-widest text-slate-500">
          Labs & Imaging
        </h3>
        <button
          type="button"
          onClick={onOpenOrderModal}
          className="rounded-full bg-emerald-600 px-4 py-1.5 text-sm font-bold text-white shadow-sm transition hover:bg-emerald-700"
        >
          + Order tests
        </button>
      </div>

      {/* Budget */}
      <div className="mb-5 rounded-xl bg-slate-50 px-4 py-3.5">
        <div className="mb-2 flex items-center justify-between">
          <span className="text-sm font-bold text-slate-600">Encounter budget</span>
          <span className="text-base font-bold text-slate-900">
            {resourcesUsed}
            <span className="font-normal text-slate-400"> / {maxResources}</span>
          </span>
        </div>
        <div className="h-2 overflow-hidden rounded-full bg-slate-200">
          <div
            className={`h-full rounded-full transition-[width] duration-500 ${barColor}`}
            style={{ width: `${pct}%` }}
          />
        </div>
        <p className="mt-1.5 text-sm text-slate-500">{remaining} points remaining</p>
      </div>

      {/* Results */}
      <div className="space-y-2">
        {orderedLabs.length === 0 ? (
          <div className="rounded-xl border-2 border-dashed border-slate-200 px-4 py-8 text-center">
            <p className="text-base font-medium text-slate-500">No labs ordered yet.</p>
            <p className="mt-1 text-sm text-slate-400">
              Start with focused cardiac enzymes and basic panels.
            </p>
          </div>
        ) : (
          orderedLabs.map((lab) => (
            <div
              key={`${lab.id}-${lab.name}`}
              className="flex items-center justify-between rounded-xl bg-slate-50 px-4 py-3"
            >
              <div>
                <p className="text-base font-semibold text-slate-900">{lab.name}</p>
                {lab.result && (
                  <p className="mt-0.5 text-sm text-slate-500">
                    {lab.result.unit
                      ? `${lab.result.value} ${lab.result.unit}`
                      : lab.result.value}
                  </p>
                )}
              </div>
              <div className="ml-3 flex shrink-0 items-center gap-2">
                {lab.result && (
                  <span className={`rounded-full px-2.5 py-0.5 text-xs font-bold ${flagStyles[lab.result.flag] ?? flagStyles.normal}`}>
                    {flagLabels[lab.result.flag] ?? "NL"}
                  </span>
                )}
                <span className="text-sm font-semibold text-slate-400">−{lab.cost}pt</span>
              </div>
            </div>
          ))
        )}
      </div>
    </section>
  );
}