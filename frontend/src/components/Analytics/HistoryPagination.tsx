"use client";
import { useEffect, useId, useRef, useState } from "react";
import { Check, ChevronDown, ChevronLeft, ChevronRight } from "lucide-react";
import { fmtIntId } from "@/utils/format";
import { clampPage } from "@/utils/emissionAnalytics";

const PAGINATION_PAGE_CLASS = "grid min-h-10 min-w-10 cursor-pointer place-items-center rounded-sm border-0 bg-transparent p-1.5 text-xs font-semibold text-(--secondary) tabular-nums enabled:hover:text-(--text) focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-(--green) disabled:cursor-default disabled:opacity-50 [&>svg]:h-[15px] [&>svg]:w-[15px]";

const PAGE_SIZE_OPTIONS = [10, 25, 50, 100];

interface HistoryPaginationProps {
    displayedCount: number;
    total: number;
    pageSize: number;
    onPageSizeChange: (size: number) => void;
    page: number;
    totalPages: number;
    onPageChange: (next: number) => void;
    loading: boolean;
    hasData: boolean;
}

export default function HistoryPagination({ displayedCount, total, pageSize, onPageSizeChange, page, totalPages, onPageChange, loading, hasData }: HistoryPaginationProps) {
    const [open, setOpen] = useState(false);
    const [active, setActive] = useState(0);
    const [pageText, setPageText] = useState(String(page));
    const [lastPage, setLastPage] = useState(page);
    const rootRef = useRef<HTMLDivElement>(null);
    const triggerRef = useRef<HTMLButtonElement>(null);
    const listId = useId();

    if (page !== lastPage) { setLastPage(page); setPageText(String(page)); }

    useEffect(() => {
        if (!open) return;
        const closeOnOutside = (event: PointerEvent) => {
            if (!rootRef.current?.contains(event.target as Node)) setOpen(false);
        };
        document.addEventListener("pointerdown", closeOnOutside);
        return () => document.removeEventListener("pointerdown", closeOnOutside);
    }, [open]);

    function openList() {
        setActive(Math.max(0, PAGE_SIZE_OPTIONS.indexOf(pageSize)));
        setOpen(true);
    }

    function commitSize(size: number) {
        onPageSizeChange(size);
        setOpen(false);
        window.requestAnimationFrame(() => triggerRef.current?.focus());
    }

    function onTriggerKeyDown(event: React.KeyboardEvent) {
        if (!open) {
            if (["ArrowDown", "ArrowUp", "Enter", " "].includes(event.key)) { event.preventDefault(); openList(); }
            return;
        }
        if (event.key === "ArrowDown" || event.key === "ArrowUp") {
            event.preventDefault();
            setActive((current) => (current + (event.key === "ArrowDown" ? 1 : -1) + PAGE_SIZE_OPTIONS.length) % PAGE_SIZE_OPTIONS.length);
        } else if (event.key === "Enter" || event.key === " ") { event.preventDefault(); commitSize(PAGE_SIZE_OPTIONS[active]); }
        else if (event.key === "Escape") { event.preventDefault(); setOpen(false); triggerRef.current?.focus(); }
        else if (event.key === "Tab") { setOpen(false); }
    }

    function commitPage() {
        const next = clampPage(pageText, totalPages);
        setPageText(String(next));
        if (next !== page) onPageChange(next);
    }

    return <nav className="my-[14px] flex items-center justify-between gap-4 text-xs text-[#94a3b8] max-[600px]:flex-row max-[600px]:flex-nowrap max-[600px]:gap-2" aria-label="Navigasi halaman riwayat">
        <div className="relative flex min-w-0 flex-wrap items-center gap-[10px] max-[600px]:flex-nowrap max-[600px]:gap-2" ref={rootRef}>
            <span className="inline-flex items-center gap-[5px]">
                Menampilkan
                <button ref={triggerRef} type="button" role="combobox" className="inline-flex min-h-10 cursor-pointer items-center gap-[3px] border-0 border-b border-dotted border-current bg-transparent px-1 font-[inherit] text-(--text) tabular-nums hover:text-(--green) focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-(--green)" aria-haspopup="listbox" aria-expanded={open}
                    aria-controls={listId} aria-activedescendant={open ? `${listId}-option-${active}` : undefined} aria-label="Jumlah baris per halaman"
                    onClick={() => (open ? setOpen(false) : openList())} onKeyDown={onTriggerKeyDown}>
                    {fmtIntId(displayedCount)}<ChevronDown className="h-3 w-3 text-(--secondary)" aria-hidden="true" />
                </button>
                dari {fmtIntId(total)} catatan
            </span>
            {open && <div className="absolute top-[calc(100%+6px)] left-0 z-20 max-h-[280px] min-w-[120px] overflow-y-auto rounded-sm border border-[#334155] bg-[#0e1d2e] p-(--space-1) shadow-[0_14px_34px_rgba(0,0,0,0.4)] animate-[select-in_0.14s_ease-out] motion-reduce:animate-none">
                <ul role="listbox" id={listId} aria-label="Jumlah baris per halaman" className="m-0 list-none p-0">
                    {PAGE_SIZE_OPTIONS.map((size, index) => <li id={`${listId}-option-${index}`} key={size} role="option" aria-selected={size === pageSize}>
                        <button type="button" tabIndex={-1}
                            className={`flex w-full cursor-pointer items-center justify-between gap-(--space-2) rounded-[5px] border-0 bg-transparent px-(--space-3) py-[9px] text-left text-xs text-(--secondary) [&>svg]:h-3.5 [&>svg]:w-3.5 ${index === active ? "bg-[#14283c] text-(--text)" : ""}${size === pageSize ? " font-(--weight-strong) text-(--green)" : ""}`}
                            onMouseEnter={() => setActive(index)} onClick={() => commitSize(size)}>
                            <span>{size}</span>
                            {size === pageSize && <Check aria-hidden="true" />}
                        </button>
                    </li>)}
                </ul>
            </div>}
        </div>
        <div className="flex min-w-0 flex-wrap items-center gap-[10px] tabular-nums max-[600px]:flex-nowrap max-[600px]:gap-2">
            <span className="inline-flex items-center gap-[5px]">
                <input type="text" inputMode="numeric" className="w-[3ch] border-0 border-b border-dotted border-current bg-transparent px-0.5 text-center font-[inherit] text-(--text) tabular-nums focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-(--green) disabled:cursor-default disabled:opacity-50" value={pageText}
                    disabled={loading || !hasData} aria-label="Halaman saat ini"
                    onChange={(event) => setPageText(event.target.value)}
                    onBlur={commitPage}
                    onKeyDown={(event) => { if (event.key === "Enter") { event.preventDefault(); commitPage(); } }} />
                dari {totalPages} halaman
            </span>
            <button type="button" className={PAGINATION_PAGE_CLASS} aria-label="Halaman sebelumnya"
                disabled={loading || page <= 1} onClick={() => onPageChange(page - 1)}><ChevronLeft aria-hidden="true" /></button>
            <button type="button" className={PAGINATION_PAGE_CLASS} aria-label="Halaman berikutnya"
                disabled={loading || !hasData || page >= totalPages} onClick={() => onPageChange(page + 1)}><ChevronRight aria-hidden="true" /></button>
        </div>
    </nav>;
}
