import type { EmissionKey } from "@/constants/emissions";

// Repeated component primitives stay as plain Tailwind class strings. Keeping
// them here avoids duplicating long utility lists without reintroducing CSS
// selectors or a runtime styling dependency.
export const PANEL_CLASS = "relative flex h-full min-w-[360px] flex-[0_0_min(430px,35vw)] flex-col overflow-hidden rounded-md border border-(--contour-strong) bg-(--surface) shadow-(--shadow-float) animate-[panel-in_0.24s_ease-out] motion-reduce:animate-none max-[1100px]:min-w-[340px] max-[1100px]:basis-[390px] max-[760px]:min-w-0 max-[760px]:flex-[1_1_100%] max-[760px]:rounded-(--radius-map)";
export const PANEL_HEADER_CLASS = "flex min-h-[68px] flex-[0_0_auto] items-center gap-3 border-b border-(--border) bg-[rgba(9,26,34,0.5)] px-4 py-2.5";
export const PANEL_ICON_CLASS = "grid h-9 w-9 place-items-center rounded-sm bg-(--brand-soft) text-(--brand-strong) [&>svg]:w-[18px]";
export const PANEL_TITLE_CLASS = "min-w-0 flex-1 [&>span]:text-[10px] [&>span]:font-bold [&>span]:tracking-[0.12em] [&>span]:text-(--muted) [&>span]:uppercase [&>h2]:mt-1 [&>h2]:mb-0 [&>h2]:line-clamp-2 [&>h2]:font-(family-name:--font-display) [&>h2]:text-[15px] [&>h2]:font-semibold [&>h2]:leading-[1.25] [&>h2]:tracking-[-0.015em] [&>h2]:[overflow-wrap:anywhere]";
export const PANEL_CLOSE_CLASS = "grid h-10 flex-[0_0_40px] cursor-pointer place-items-center rounded-sm border border-(--border) bg-(--surface-raised) text-(--secondary) transition-colors hover:border-(--contour-strong) hover:text-(--text) [&>svg]:w-4";
export const PANEL_CONTENT_CLASS = "min-h-0 flex-1 overflow-y-auto overscroll-contain [scrollbar-color:var(--contour-strong)_transparent] [scrollbar-gutter:stable] [scrollbar-width:thin]";
export const PANEL_SECTION_CLASS = "border-b border-(--border) px-4 py-5 last:border-b-0 max-[420px]:px-[14px] max-[420px]:py-[18px]";
export const SEGMENT_PANEL_HEADER_CLASS = PANEL_HEADER_CLASS;
export const SEGMENT_PANEL_TITLE_CLASS = PANEL_TITLE_CLASS;
export const SEGMENT_PANEL_CONTENT_CLASS = `${PANEL_CONTENT_CLASS} pb-1 [scrollbar-gutter:stable] [&::-webkit-scrollbar]:w-2 [&::-webkit-scrollbar-track]:bg-transparent [&::-webkit-scrollbar-thumb]:rounded-full [&::-webkit-scrollbar-thumb]:border-2 [&::-webkit-scrollbar-thumb]:border-(--surface) [&::-webkit-scrollbar-thumb]:bg-(--contour-strong)`;
export const SEGMENT_SECTION_CLASS = PANEL_SECTION_CLASS;
export const SEGMENT_OVERVIEW_CLASS = "mx-4 mt-3 grid grid-cols-[minmax(0,1fr)_auto] items-start gap-x-3 gap-y-2 rounded-md border border-(--border) bg-(--surface-raised) px-3.5 py-3 max-[420px]:mx-[14px] [&>strong]:min-w-0 [&>strong]:font-(family-name:--font-display) [&>strong]:text-[15px] [&>strong]:font-semibold [&>strong]:leading-[1.3] [&>strong]:[overflow-wrap:anywhere] [&>span]:text-right [&>span]:text-[11px] [&>span]:leading-[1.4] [&>span]:text-(--secondary) [&>span]:[overflow-wrap:anywhere]";
export const SEGMENT_EMPTY_CLASS = "m-0 flex min-h-[58px] items-center justify-center gap-[9px] rounded-md border border-dashed border-(--border) bg-(--surface-raised) p-[13px] text-center text-[11px] leading-[1.5] text-(--muted)";
export const SEGMENT_STATE_CLASS = "mx-4 my-4 flex min-h-[150px] flex-col items-center justify-center gap-2 rounded-md border border-dashed border-(--border) bg-(--surface-raised) p-5 text-center text-[11px] leading-[1.55] text-(--secondary) [&>strong]:font-(family-name:--font-display) [&>strong]:text-[13px] [&>span]:max-w-[28ch] [&>span]:text-[10px]";
export const DATA_MISSING_CLASS = "text-[11px]! font-medium! leading-[1.4]! tracking-normal! text-(--muted)!";
export const CRITERIA_GRID_CLASS = "grid grid-cols-2 gap-[9px] max-[420px]:grid-cols-1 [&>div]:grid [&>div]:min-h-12 [&>div]:min-w-0 [&>div]:grid-cols-[minmax(0,0.7fr)_minmax(0,1.6fr)] [&>div]:items-center [&>div]:gap-2 [&>div]:rounded-sm [&>div]:border [&>div]:border-(--border) [&>div]:bg-(--surface-raised) [&>div]:px-[11px] [&>div]:py-[10px] [&>div]:tabular-nums [&>div]:[overflow-wrap:anywhere] [&>div:last-child:nth-child(odd)]:col-span-full [&>div:last-child:nth-child(odd)]:grid-cols-[minmax(0,1fr)_auto] [&_span]:text-[11px] [&_span]:leading-[1.3] [&_span]:text-(--muted) [&_strong]:text-right [&_strong]:text-xs [&_strong]:leading-[1.35] [&_strong]:tabular-nums [&_strong]:[overflow-wrap:anywhere]";

export const STAT_GRID_CLASS = "grid grid-cols-2 gap-2";
export const STAT_CARD_CLASS = "rounded-sm border border-(--border) bg-(--surface-raised) px-3 py-[11px]";
export const STAT_LABEL_CLASS = "flex items-center gap-1.5 text-[11px] font-bold";
export const STAT_VALUE_CLASS = "mt-[7px] font-(family-name:--font-data) text-lg font-semibold text-(--text) tabular-nums [&>small]:ml-[5px] [&>small]:text-[11px] [&>small]:font-normal [&>small]:text-(--muted)";
export const POLLUTANT_DOT_CLASS = "h-[7px] w-[7px] flex-[0_0_7px] rounded-full bg-current";
export const POLLUTANT_TEXT_CLASS: Record<EmissionKey, string> = {
    tsp: "text-(--tsp)",
    nox: "text-(--nox)",
    so2: "text-(--so2)",
    hc: "text-(--hc)",
    co: "text-(--co)",
    co2: "text-(--co2)",
    ch4: "text-(--ch4)",
    n2o: "text-(--n2o)",
};

export const DATA_EMPTY_CLASS = "flex min-h-[72px] items-center justify-center gap-[9px] rounded-md border border-dashed border-(--border) text-[11px] text-(--secondary)";
export const ANALYTICS_NOTE_CLASS = "mt-3 mb-0.5 text-xs leading-[1.65] text-(--muted)";
export const TEXT_CAPTION_CLASS = "mt-0 mb-[10px] text-(--text-small) leading-(--leading-body) text-(--secondary)";
export const ESTIMATE_BADGE_CLASS = "inline-flex items-center rounded-(--radius-badge) bg-[rgba(245,165,36,0.12)] px-2 py-1 text-[10px] font-bold tracking-[0.08em] text-[#f5c35f] uppercase";

export const PAGE_CONTAINER_CLASS = "h-full overflow-auto overscroll-contain px-5 pt-[18px] pb-[30px] [scrollbar-gutter:stable] max-[760px]:px-1 max-[760px]:pt-3 max-[760px]:pb-5";
export const PAGE_CARD_CLASS = "mb-[14px] rounded-md border border-(--border) bg-(--card) p-4 max-[760px]:p-[13px]";
export const ANALYTICS_BUTTON_CLASS = "min-h-(--control-height) cursor-pointer rounded-sm border border-(--contour-strong) bg-(--surface-raised) px-[14px] py-[9px] text-xs font-(--weight-label) text-(--text) transition-[border-color,background,color] duration-150 hover:border-(--selection) hover:bg-(--surface-hover) disabled:cursor-default disabled:opacity-45";
export const FOCUS_RING_CLASS = "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-(--selection)";
export const PAGE_CARD_GRID_CLASS = "mb-[14px] grid grid-cols-4 gap-[10px] max-[760px]:grid-cols-2";
export const SUMMARY_METRIC_CLASS = "flex flex-col gap-2 [&>span]:text-[11px] [&>span]:font-bold [&>strong]:font-(family-name:--font-data) [&>strong]:text-2xl [&>small]:text-[11px] [&>small]:text-(--muted)";
export const CHART_CLASS = "h-80 w-full min-w-0 max-[600px]:h-[280px]";
export const CHART_SMALL_CLASS = "h-[250px] max-[600px]:h-[230px]";
export const CHART_INTERACTIVE_CLASS = "outline-none focus-visible:rounded-sm focus-visible:outline-2 focus-visible:outline-offset-3 focus-visible:outline-(--green)";
export const ANALYTICS_CHART_GRID_CLASS = "mb-5 grid grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)] gap-[14px] max-[1000px]:grid-cols-1";
export const UNAVAILABLE_STATE_CLASS = "flex min-h-[110px] flex-col items-center justify-center gap-[7px] rounded-md border border-dashed border-(--border) bg-(--surface-sunken) px-4 text-center text-[11px] text-(--secondary) [&>strong]:text-xs [&>strong]:text-(--text)";
export const ANALYTICS_ERROR_CLASS = "my-3 rounded-sm border border-[rgba(239,68,68,0.24)] bg-[rgba(239,68,68,0.08)] p-3 text-[12px] leading-[1.55] text-[#fda4af]";
export const ANIMATE_IN_CLASS = "animate-[card-in_0.42s_ease-out_both] motion-reduce:animate-none";
export const TABLE_WRAP_CLASS = "overflow-x-auto rounded-sm border border-(--border) bg-(--surface-sunken)";
export const PRIORITY_TABLE_CLASS = "w-full border-collapse text-[11px] [&_thead]:bg-(--surface-raised) [&_th]:whitespace-nowrap [&_th]:border-b [&_th]:border-(--contour-strong) [&_th]:px-[10px] [&_th]:py-2.5 [&_th]:text-left [&_th]:text-[9px] [&_th]:tracking-[0.09em] [&_th]:text-(--muted) [&_th]:uppercase [&_th]:tabular-nums [&_td]:whitespace-nowrap [&_td]:border-b [&_td]:border-(--border) [&_td]:px-[10px] [&_td]:py-2.5 [&_td]:text-left [&_td]:tabular-nums [&_tbody>tr]:transition-colors [&_tbody>tr:hover]:bg-(--selection-soft) [&_tbody>tr:last-child>td]:border-b-0";
