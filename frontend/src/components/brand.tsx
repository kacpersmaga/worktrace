import Link from "next/link";

export function Logo({ size = 22 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" aria-hidden>
      <rect x="1" y="1" width="22" height="22" rx="6" fill="var(--ink)" />
      <path d="M6 15.5 9.5 9l3.5 5 3-3.5 2 2.5" fill="none" stroke="var(--surface)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="18" cy="13" r="1.6" fill="var(--accent)" />
    </svg>
  );
}

export function Brand() {
  return (
    <Link href="/" className="inline-flex items-center gap-2 text-[15px] font-semibold tracking-tight text-ink">
      <Logo />
      WorkTrace
    </Link>
  );
}
