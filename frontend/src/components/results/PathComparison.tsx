interface PathComparisonProps {
  traineePath: string[];
  learningPoints: string[];
}

export function PathComparison({
  traineePath,
  learningPoints,
}: PathComparisonProps) {
  return (
    <section className="mt-4 grid gap-4 rounded-3xl border border-slate-200 bg-white/80 p-5 shadow-sm">
      <div>
        <h3 className="text-sm font-semibold text-slate-900">
          Your diagnostic path
        </h3>
        <ol className="mt-2 space-y-1.5 text-xs text-slate-700">
          {traineePath.map((step, idx) => (
            <li key={`trainee-${idx}`} className="flex gap-2">
              <span className="mt-0.5 inline-flex h-5 w-5 items-center justify-center rounded-full bg-slate-900 text-[10px] font-semibold text-white">
                {idx + 1}
              </span>
              <span>{step}</span>
            </li>
          ))}
        </ol>
      </div>

      <div>
        <h3 className="mb-1 text-sm font-semibold text-slate-900">
          Learning points
        </h3>
        <ul className="space-y-1.5 text-xs text-slate-700">
          {learningPoints.map((point, idx) => (
            <li key={`learning-${idx}`} className="flex gap-2">
              <span className="mt-1 h-1.5 w-1.5 rounded-full bg-emerald-500" />
              <span>{point}</span>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}

