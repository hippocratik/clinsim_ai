export default function Loading() {
  return (
    <div className="mx-auto max-w-6xl space-y-4 py-6">
      <div className="rounded-3xl border border-slate-200 bg-white/80 p-5 shadow-sm">
        <div className="h-4 w-40 animate-pulse rounded-full bg-slate-200" />
        <div className="mt-3 h-3 w-64 animate-pulse rounded-full bg-slate-100" />
        <div className="mt-2 flex gap-2">
          <div className="h-5 w-20 animate-pulse rounded-full bg-emerald-100" />
          <div className="h-5 w-24 animate-pulse rounded-full bg-slate-100" />
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        {Array.from({ length: 2 }).map((_, idx) => (
          <div
            key={idx}
            className="flex flex-col justify-between rounded-3xl border border-slate-200 bg-white/80 p-4 shadow-sm"
          >
            <div className="space-y-2">
              <div className="h-4 w-52 animate-pulse rounded-full bg-slate-200" />
              <div className="h-3 w-full animate-pulse rounded-full bg-slate-100" />
              <div className="h-3 w-32 animate-pulse rounded-full bg-slate-100" />
            </div>
            <div className="mt-3 flex items-center justify-between">
              <div className="flex gap-2">
                <div className="h-5 w-16 animate-pulse rounded-full bg-slate-100" />
                <div className="h-5 w-14 animate-pulse rounded-full bg-slate-100" />
              </div>
              <div className="h-7 w-24 animate-pulse rounded-full bg-emerald-200" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

