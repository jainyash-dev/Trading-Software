import type { RouteId } from "../navigation/routes";

/** 16 px line icons drawn for GTF. Decorative only; labels always carry the meaning. */
const PATHS: Record<RouteId | "sun" | "moon" | "search" | "collapse" | "expand" | "shield", string> = {
  overview: "M2.5 13.5h11M4 11V7m3 4V4m3 7V8m3 3V5",
  watchlists: "M5 4h8M5 8h8M5 12h8M2.5 4h.01M2.5 8h.01M2.5 12h.01",
  analysis: "M2.5 12.5l3-4 2.5 2 3.5-5 2 2.5M2.5 2.5v11h11",
  scanner: "M7 12a5 5 0 1 1 0-10 5 5 0 0 1 0 10zm3.6-1.4L14 14M5 7h4M7 5v4",
  opportunities: "M8 2l1.8 3.7 4 .6-2.9 2.8.7 4L8 11.2 4.4 13.1l.7-4L2.2 6.3l4-.6z",
  history: "M8 4.5V8l2.5 1.5M2.6 6.5A5.5 5.5 0 1 1 3 10.5M2.5 3v3.5H6",
  plans: "M4 2.5h6l2.5 2.5v8.5H4zM6 7h4.5M6 9.5h4.5M6 12h2.5",
  portfolio: "M2.5 5h11v8h-11zM5.5 5V3.5h5V5M2.5 8.5h11",
  risk: "M8 2l5.5 2v4c0 3-2.4 5.2-5.5 6-3.1-.8-5.5-3-5.5-6V4zM8 5.5v3M8 10.8h.01",
  journal: "M3.5 2.5h8a1 1 0 0 1 1 1v10h-8a1 1 0 0 1-1-1zM3.5 11.5h9M6 5.5h4M6 8h4",
  backtest: "M2.5 13.5h11M3.5 10.5l3-3 2 2 4-5M10.5 4.5h2v2",
  analytics: "M8 2.5v5.5h5.5A5.5 5.5 0 1 1 8 2.5zM10 1.5a4.5 4.5 0 0 1 4.5 4.5H10z",
  reports: "M4 1.5h5.5L12 4v10.5H4zM6 8.5h4M6 11h4M6 6h1.5",
  assistant: "M2.5 3.5h11v7.5H7l-3 2.5V11H2.5zM5.5 7.2h.01M8 7.2h.01M10.5 7.2h.01",
  paper: "M3 13.5V3.5l2.5-1 2.5 1 2.5-1 2.5 1v10l-2.5-1-2.5 1-2.5-1z",
  data: "M2.5 4c0-1 2.5-1.8 5.5-1.8S13.5 3 13.5 4s-2.5 1.8-5.5 1.8S2.5 5 2.5 4zm0 0v8c0 1 2.5 1.8 5.5 1.8s5.5-.8 5.5-1.8V4M2.5 8c0 1 2.5 1.8 5.5 1.8S13.5 9 13.5 8",
  jobs: "M1.5 8h3l1.5-4 3 8 1.5-4h4",
  settings: "M8 10a2 2 0 1 0 0-4 2 2 0 0 0 0 4zM8 1.5v2M8 12.5v2M1.5 8h2M12.5 8h2M3.4 3.4l1.4 1.4M11.2 11.2l1.4 1.4M3.4 12.6l1.4-1.4M11.2 4.8l1.4-1.4",
  sun: "M8 11a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM8 1v1.5M8 13.5V15M1 8h1.5M13.5 8H15M3 3l1 1M12 12l1 1M3 13l1-1M12 4l1-1",
  moon: "M13.5 9.5A5.5 5.5 0 0 1 6.5 2.5a5.5 5.5 0 1 0 7 7z",
  search: "M7 12a5 5 0 1 1 0-10 5 5 0 0 1 0 10zm3.6-1.4L14 14",
  collapse: "M10 3.5L5.5 8l4.5 4.5",
  expand: "M6 3.5L10.5 8 6 12.5",
  shield: "M8 2l5.5 2v4c0 3-2.4 5.2-5.5 6-3.1-.8-5.5-3-5.5-6V4z",
};

export function Icon(props: { name: keyof typeof PATHS; size?: number; className?: string }) {
  const size = props.size ?? 16;
  return (
    <svg
      aria-hidden="true"
      focusable="false"
      width={size}
      height={size}
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.35"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={props.className}
    >
      <path d={PATHS[props.name]} />
    </svg>
  );
}
