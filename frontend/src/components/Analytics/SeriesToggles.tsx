export interface SeriesToggleItem {
    key: string;
    label: string;
    color: string;
}

export default function SeriesToggles({
    items,
    active,
    onToggle,
    label,
    compact = false,
}: {
    items: SeriesToggleItem[];
    active: ReadonlySet<string>;
    onToggle: (key: string) => void;
    label: string;
    compact?: boolean;
}) {
    return (
        <div className={`flex flex-wrap items-center gap-1.5 ${compact ? "py-1" : "py-2"}`} role="group" aria-label={label}>
            {items.map((item) => {
                const selected = active.has(item.key);
                return (
                    <button
                        key={item.key}
                        type="button"
                        aria-pressed={selected}
                        onClick={() => onToggle(item.key)}
                        className={`inline-flex cursor-pointer items-center gap-1.5 rounded-[var(--radius-badge)] border px-2.5 font-semibold transition-[border-color,background,color,opacity] duration-150 ${compact ? "min-h-7 text-[10px]" : "min-h-8 text-[11px]"} ${selected ? "border-[var(--contour-strong)] bg-[var(--surface-raised)] text-[var(--text)]" : "border-transparent bg-[var(--surface-sunken)] text-[var(--muted)] opacity-55 hover:opacity-85"}`}
                    >
                        <span className={`h-[3px] w-3 ${selected ? "opacity-100" : "opacity-45"}`} style={{ backgroundColor: item.color }} aria-hidden="true" />
                        {item.label}
                    </button>
                );
            })}
        </div>
    );
}
