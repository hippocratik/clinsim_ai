"use client";

interface ErrorProps {
  error: Error;
  reset: () => void;
}

export default function ErrorBoundary({ error, reset }: ErrorProps) {
  return (
    <div className="mx-auto flex min-h-[60vh] max-w-2xl flex-col items-center justify-center gap-4 text-center">
      <h2 className="text-lg font-semibold text-rose-700">
        Something went wrong while loading this case.
      </h2>
      <p className="text-sm text-slate-600">
        {error.message || "An unexpected error occurred. You can try again or return to the case list."}
      </p>
      <div className="mt-2 flex gap-3">
        <button
          type="button"
          onClick={reset}
          className="rounded-full bg-emerald-600 px-4 py-2 text-xs font-semibold text-white shadow-sm hover:bg-emerald-700"
        >
          Try again
        </button>
        <a
          href="/"
          className="rounded-full bg-white px-4 py-2 text-xs font-semibold text-slate-700 ring-1 ring-slate-200 hover:bg-slate-50"
        >
          Back to case list
        </a>
      </div>
    </div>
  );
}

