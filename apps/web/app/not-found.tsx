import Link from "next/link";

export default function NotFound() {
  return (
    <div className="flex flex-col items-center gap-3 rounded-xl border border-neutral-200 bg-white p-6 text-center">
      <p className="text-sm font-medium text-neutral-800">Sayfa bulunamadi.</p>
      <Link href="/" className="rounded-full bg-brand-500 px-4 py-2 text-sm font-medium text-white">
        Ana sayfaya don
      </Link>
    </div>
  );
}
