import type { EmissionKey } from "@/constants/emissions";

// Repeated component primitives stay as plain Tailwind class strings. Keeping
// them here avoids duplicating long utility lists without reintroducing CSS
// selectors or a runtime styling dependency.
export const PANEL_CLASS = "flex h-full min-w-[360px] flex-[0_0_min(430px,35vw)] flex-col overflow-hidden rounded-xl border border-[var(--border)] bg-[#081522] shadow-[0_16px_42px_rgba(0,0,0,0.24)] animate-[panel-in_0.24s_ease-out] max-[1100px]:min-w-[340px] max-[1100px]:basis-[390px] max-[760px]:min-w-0 max-[760px]:flex-[1_1_100%] max-[760px]:rounded-[10px]";
export const PANEL_HEADER_CLASS = "flex flex-[0_0_64px] items-center gap-[11px] border-b border-[var(--border)] px-[15px] max-[760px]:basis-[58px]";
export const PANEL_ICON_CLASS = "grid h-[34px] w-[34px] place-items-center rounded-lg bg-[rgba(34,197,94,0.1)] text-[#4ade80] [&>svg]:w-[18px]";
export const PANEL_TITLE_CLASS = "min-w-0 flex-1 [&>span]:text-[7px] [&>span]:font-bold [&>span]:tracking-[0.14em] [&>span]:text-[var(--muted)] [&>h2]:mt-1 [&>h2]:mb-0 [&>h2]:overflow-hidden [&>h2]:text-ellipsis [&>h2]:whitespace-nowrap [&>h2]:font-[var(--font-display)] [&>h2]:text-xs [&>h2]:font-[650]";
export const PANEL_CLOSE_CLASS = "grid h-[30px] flex-[0_0_30px] cursor-pointer place-items-center rounded-[7px] border border-[var(--border)] bg-[#0c1c2d] text-[var(--secondary)] hover:border-[#42536a] hover:text-white [&>svg]:w-[15px]";
export const PANEL_CONTENT_CLASS = "min-h-0 flex-1 overflow-y-auto [scrollbar-color:#26364a_transparent] [scrollbar-width:thin]";
export const PANEL_SECTION_CLASS = "border-b border-[var(--border)] p-[15px]";
export const SEGMENT_PANEL_HEADER_CLASS = "flex min-h-[68px] flex-[0_0_auto] items-center gap-[10px] border-b border-[rgba(148,163,184,0.12)] px-[14px] py-[9px]";
export const SEGMENT_PANEL_TITLE_CLASS = "min-w-0 flex-1 [&>span]:text-[8px] [&>span]:font-bold [&>span]:leading-none [&>span]:tracking-[0.13em] [&>span]:text-[var(--muted)] [&>h2]:mt-1 [&>h2]:mb-0 [&>h2]:line-clamp-2 [&>h2]:font-[var(--font-display)] [&>h2]:text-sm [&>h2]:font-[650] [&>h2]:leading-[1.25] [&>h2]:[overflow-wrap:anywhere]";
export const SEGMENT_PANEL_CONTENT_CLASS = `${PANEL_CONTENT_CLASS} pb-1 [scrollbar-color:#34455b_transparent] [scrollbar-gutter:stable] [&::-webkit-scrollbar]:w-2 [&::-webkit-scrollbar-track]:bg-transparent [&::-webkit-scrollbar-thumb]:rounded-full [&::-webkit-scrollbar-thumb]:border-2 [&::-webkit-scrollbar-thumb]:border-[#081522] [&::-webkit-scrollbar-thumb]:bg-[#34455b] hover:[&::-webkit-scrollbar-thumb]:bg-[#465a73]`;
export const SEGMENT_SECTION_CLASS = "border-b border-[rgba(148,163,184,0.1)] px-4 py-5 last:border-b-0 max-[420px]:px-[14px] max-[420px]:py-[18px]";
export const SEGMENT_OVERVIEW_CLASS = "mx-4 mt-[10px] grid grid-cols-[minmax(0,1fr)_auto] items-start gap-x-[10px] gap-y-1.5 rounded-[9px] border border-[rgba(148,163,184,0.12)] bg-[rgba(14,29,46,0.88)] px-[13px] py-3 max-[420px]:mx-[14px] [&>strong]:min-w-0 [&>strong]:text-sm [&>strong]:leading-[1.35] [&>strong]:[overflow-wrap:anywhere] [&>span]:whitespace-nowrap [&>span]:text-right [&>span]:text-[11px] [&>span]:leading-[1.35] [&>span]:text-[var(--secondary)]";
export const SEGMENT_EMPTY_CLASS = "m-0 flex min-h-[58px] items-center justify-center gap-[9px] rounded-lg border border-dashed border-[rgba(148,163,184,0.12)] bg-[rgba(14,29,46,0.4)] p-[13px] text-center text-[10px] leading-[1.5] text-[#718198]";
export const SEGMENT_STATE_CLASS = "flex min-h-[150px] flex-col items-center justify-center gap-[9px] p-4 text-center text-[11px] leading-[1.5] text-[var(--secondary)] [&>span]:text-[10px]";
export const DATA_MISSING_CLASS = "text-[10px]! font-medium! leading-[1.4]! tracking-normal! text-[#718198]!";
export const CRITERIA_GRID_CLASS = "grid grid-cols-2 gap-[9px] max-[420px]:grid-cols-1 [&>div]:grid [&>div]:min-h-12 [&>div]:min-w-0 [&>div]:grid-cols-[minmax(0,0.7fr)_minmax(0,1.6fr)] [&>div]:items-center [&>div]:gap-2 [&>div]:rounded-[7px] [&>div]:border [&>div]:border-[rgba(148,163,184,0.1)] [&>div]:bg-[rgba(14,29,46,0.75)] [&>div]:px-[11px] [&>div]:py-[10px] [&>div]:tabular-nums [&>div]:[overflow-wrap:anywhere] [&>div:last-child:nth-child(odd)]:col-span-full [&>div:last-child:nth-child(odd)]:grid-cols-[minmax(0,1fr)_auto] [&_span]:text-[10px] [&_span]:leading-[1.3] [&_span]:text-[#7f8fa5] [&_strong]:text-right [&_strong]:text-xs [&_strong]:leading-[1.35] [&_strong]:tabular-nums [&_strong]:[overflow-wrap:anywhere]";

export const STAT_GRID_CLASS = "grid grid-cols-2 gap-2";
export const STAT_CARD_CLASS = "rounded-lg border border-[var(--border)] bg-[var(--card-2)] px-3 py-[11px]";
export const STAT_LABEL_CLASS = "flex items-center gap-1.5 text-[9px] font-extrabold";
export const STAT_VALUE_CLASS = "mt-[7px] text-lg font-[650] text-[var(--text)] tabular-nums [&>small]:ml-[5px] [&>small]:text-[8px] [&>small]:font-normal [&>small]:text-[var(--muted)]";
export const POLLUTANT_DOT_CLASS = "h-[7px] w-[7px] flex-[0_0_7px] rounded-full bg-current";
export const POLLUTANT_TEXT_CLASS: Record<EmissionKey, string> = {
    tsp: "text-[var(--tsp)]",
    nox: "text-[var(--nox)]",
    so2: "text-[var(--so2)]",
    hc: "text-[var(--hc)]",
    co: "text-[var(--co)]",
    co2: "text-[var(--co2)]",
    ch4: "text-[var(--ch4)]",
    n2o: "text-[var(--n2o)]",
};

export const DATA_EMPTY_CLASS = "flex min-h-[72px] items-center justify-center gap-[9px] rounded-lg border border-dashed border-[var(--border)] text-[10px] text-[var(--secondary)]";
export const ANALYTICS_NOTE_CLASS = "mt-3 mb-0.5 text-xs leading-[1.65] text-[var(--muted)]";
export const TEXT_CAPTION_CLASS = "mt-0 mb-[10px] text-[var(--text-small)] leading-[var(--leading-body)] text-[var(--secondary)]";
export const ESTIMATE_BADGE_CLASS = "inline-flex items-center rounded-full bg-[rgba(245,165,36,0.12)] px-2 py-1 text-[8px] font-extrabold tracking-[0.08em] text-[#f5c35f] uppercase";

export const PAGE_CONTAINER_CLASS = "h-full overflow-auto px-5 pt-[18px] pb-[30px] max-[760px]:px-1 max-[760px]:pt-3 max-[760px]:pb-5";
export const PAGE_CARD_CLASS = "mb-[14px] rounded-[10px] border border-[var(--border)] bg-[var(--card)] p-4 max-[760px]:p-[13px]";
export const ANALYTICS_BUTTON_CLASS = "min-h-[var(--control-height)] cursor-pointer rounded-[var(--radius-sm)] border border-[#355269] bg-[#142e3b] px-[14px] py-[9px] text-xs font-[var(--weight-label)] text-[#dceee7] transition-[border-color,background] duration-180 hover:border-[#22c55e] disabled:cursor-default disabled:opacity-45";
export const FOCUS_RING_CLASS = "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--green)]";
export const PAGE_CARD_GRID_CLASS = "mb-[14px] grid grid-cols-4 gap-[10px] max-[760px]:grid-cols-2";
export const SUMMARY_METRIC_CLASS = "flex flex-col gap-2 [&>span]:text-[10px] [&>span]:font-extrabold [&>strong]:text-2xl [&>small]:text-[9px] [&>small]:text-[var(--muted)]";
export const CHART_CLASS = "h-80 w-full min-w-0";
export const CHART_SMALL_CLASS = "h-[250px]";
export const CHART_INTERACTIVE_CLASS = "outline-none focus-visible:rounded-[var(--radius-sm)] focus-visible:outline-2 focus-visible:outline-offset-3 focus-visible:outline-[var(--green)]";
export const ANALYTICS_CHART_GRID_CLASS = "mb-5 grid grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)] gap-5 max-[1000px]:grid-cols-1";
export const UNAVAILABLE_STATE_CLASS = "flex min-h-[110px] flex-col items-center justify-center gap-[7px] text-center text-[10px] text-[var(--secondary)] [&>strong]:text-xs [&>strong]:text-[#cbd5e1]";
export const ANALYTICS_ERROR_CLASS = "p-3 text-[13px] text-[#fda4af]";
export const ANIMATE_IN_CLASS = "animate-[card-in_0.42s_ease-out_both] motion-reduce:animate-none";
export const TABLE_WRAP_CLASS = "overflow-x-auto";
export const PRIORITY_TABLE_CLASS = "w-full border-collapse text-[10px] [&_th]:whitespace-nowrap [&_th]:border-b [&_th]:border-[var(--border)] [&_th]:px-[10px] [&_th]:py-2 [&_th]:text-left [&_th]:text-[8px] [&_th]:tracking-[0.08em] [&_th]:text-[var(--muted)] [&_th]:uppercase [&_th]:tabular-nums [&_td]:whitespace-nowrap [&_td]:border-b [&_td]:border-[var(--border)] [&_td]:px-[10px] [&_td]:py-2 [&_td]:text-left [&_td]:tabular-nums";
