"use client";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="flex flex-col items-center gap-3 rounded-xl border border-red-200 bg-red-50 p-6 text-center">
      <p className="text-sm font-medium text-red-700">Bir seyler ters gitti.</p>
      <p className="text-xs text-red-600">
        Cevrimdisiysan bu normal olabilir - baglanti gelince tekrar dene.
      </p>
      <button
        type="button"
        onClick={reset}
        className="rounded-full bg-red-600 px-4 py-2 text-sm font-medium text-white"
      >
        Tekrar dene
      </button>
    </div>
  );
}
