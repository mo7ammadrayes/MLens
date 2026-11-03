import { Link } from "react-router-dom";

// MLens mark: a lens framing three rising bars (data seen through a lens).
export function BrandMark({ size = 28, inverted = false }: { size?: number; inverted?: boolean }) {
  const bg = inverted ? "#fff" : "#121212";
  const fg = inverted ? "#121212" : "#fff";
  return (
    <svg viewBox="0 0 32 32" width={size} height={size} aria-hidden>
      <rect width="32" height="32" rx="4" fill={bg} />
      <circle cx="14.5" cy="14.5" r="8.2" fill="none" stroke={fg} strokeWidth="2.6" />
      <path d="M20.6 20.6l5.4 5.4" stroke={fg} strokeWidth="3.2" strokeLinecap="square" />
      <rect x="10.4" y="15.2" width="2.2" height="3.6" fill={fg} />
      <rect x="13.4" y="12.6" width="2.2" height="6.2" fill={fg} />
      <rect x="16.4" y="10.2" width="2.2" height="8.6" fill={fg} />
    </svg>
  );
}

export function Brand({ to = "/", className = "lp-brand" }: { to?: string; className?: string }) {
  return (
    <Link to={to} className={className} aria-label="MLens home">
      <BrandMark />
      <span>MLens</span>
    </Link>
  );
}
