import Link from "next/link";

export default function AppHeader() {
  return (
    <header className="sticky top-0 z-20 border-b border-brand-100 bg-white/95 backdrop-blur">
      <div className="mx-auto flex max-w-md items-center justify-between px-4 py-3">
        <Link href="/" className="flex items-center gap-2">
          <span className="flex h-8 w-8 items-center justify-center rounded-full bg-brand-500 text-white">
            {/* simple leaf glyph */}
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path
                d="M12 3c-5 3-8 7-8 12 0 3 2.5 5 5.5 5h1.5c3 0 5.5-2.5 5.5-6 0-4-2-8-4.5-11z"
                fill="white"
              />
            </svg>
          </span>
          <span className="text-lg font-semibold text-brand-700">AgriTwin</span>
        </Link>
        <Link
          href="/onboarding"
          className="rounded-full bg-brand-500 px-3 py-1.5 text-sm font-medium text-white active:bg-brand-600"
        >
          + Yeni parsel
        </Link>
      </div>
    </header>
  );
}
