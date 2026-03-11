import type { OrderedLab } from "@/lib/types";

interface LabsPanelProps {
  orderedLabs: OrderedLab[];
  resourcesUsed: number;
  maxResources: number;
  onOpenOrderModal: () => void;
}

export function LabsPanel({
  orderedLabs,
  resourcesUsed,
  maxResources,
  onOpenOrderModal,
}: LabsPanelProps) {
  const remaining = Math.max(maxResources - resourcesUsed, 0);
  const budgetPercent = Math.min(
    Math.round((resourcesUsed / maxResources) * 100),
    100,
  );

  return (
    <section className="flex flex-col gap-3 rounded-2xl border border-slate-200 bg-white/70 p-4 shadow-sm">
      <div className="flex items-center justify-between">
        <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          Labs & Imaging
        </h3>
        <button
          type="button"
          onClick={onOpenOrderModal}
          className="rounded-full bg-slate-900 px-3 py-1 text-xs font-semibold text-white shadow-sm hover:bg-slate-800"
        >
          Order tests
        </button>
      </div>

      <div className="space-y-2">
        <div className="flex items-center justify-between text-[11px] text-slate-600">
          <span>Resource budget</span>
          <span>
            Used {resourcesUsed} / {maxResources} (remaining {remaining})
          </span>
        </div>
        <div className="h-2 overflow-hidden rounded-full bg-slate-100">
          <div
            className="h-full rounded-full bg-amber-500 transition-[width]"
            style={{ width: `${budgetPercent}%` }}
          />
        </div>
      </div>

      <div className="mt-1 space-y-1.5 text-xs">
        {orderedLabs.length === 0 ? (
          <p className="text-slate-500">
            No labs ordered yet. Start with focused cardiac enzymes and basic
            panels.
          </p>
        ) : (
          orderedLabs.map((lab) => (
            <div
              key={`${lab.id}-${lab.name}`}
              className="flex items-start justify-between rounded-xl bg-slate-50 px-3 py-2"
            >
              <div>
                <p className="font-medium text-slate-900">{lab.name}</p>
                {lab.result && (
                  <p className="mt-0.5 text-[11px] text-slate-600">
                    {lab.result.unit
                      ? `${lab.result.value} ${lab.result.unit} · ${lab.result.flag}`
                      : lab.result.value}
                  </p>
                )}
              </div>
              <span className="ml-2 text-[11px] font-semibold text-slate-700">
                −{lab.cost}
              </span>
            </div>
          ))
        )}
      </div>
    </section>
  );
}

