"use client";
import { useEffect, useId, useRef, useState } from "react";
import { Check, ChevronDown, ChevronLeft, ChevronRight } from "lucide-react";
import { fmtIntId } from "@/utils/format";
import { clampPage } from "@/utils/emissionAnalytics";

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
        else if (event.key === "Escape") { event.preventDefault(); setOpen(false); }
        else if (event.key === "Tab") { setOpen(false); }
    }

    function commitPage() {
        const next = clampPage(pageText, totalPages);
        setPageText(String(next));
        if (next !== page) onPageChange(next);
    }

    return <nav className="analytics-pagination history-pagination" aria-label="Navigasi halaman riwayat">
        <div className="history-pagination-left" ref={rootRef}>
            <span className="history-count">
                Menampilkan
                <button type="button" className="history-count-trigger" aria-haspopup="listbox" aria-expanded={open}
                    aria-controls={listId} aria-label="Jumlah baris per halaman"
                    onClick={() => (open ? setOpen(false) : openList())} onKeyDown={onTriggerKeyDown}>
                    {fmtIntId(displayedCount)}<ChevronDown className="history-count-chevron" aria-hidden="true" />
                </button>
                dari {fmtIntId(total)} catatan
            </span>
            {open && <div className="history-count-menu">
                <ul role="listbox" id={listId} aria-label="Jumlah baris per halaman" className="ui-select-list">
                    {PAGE_SIZE_OPTIONS.map((size, index) => <li key={size} role="option" aria-selected={size === pageSize}>
                        <button type="button" tabIndex={-1}
                            className={`ui-select-option${index === active ? " is-active" : ""}${size === pageSize ? " is-selected" : ""}`}
                            onMouseEnter={() => setActive(index)} onClick={() => commitSize(size)}>
                            <span>{size}</span>
                            {size === pageSize && <Check aria-hidden="true" />}
                        </button>
                    </li>)}
                </ul>
            </div>}
        </div>
        <div className="history-pagination-right">
            <span className="history-page-jump">
                <input type="text" inputMode="numeric" className="history-page-input" value={pageText}
                    disabled={loading || !hasData} aria-label="Halaman saat ini"
                    onChange={(event) => setPageText(event.target.value)}
                    onBlur={commitPage}
                    onKeyDown={(event) => { if (event.key === "Enter") { event.preventDefault(); commitPage(); } }} />
                dari {totalPages} halaman
            </span>
            <button type="button" className="pagination-page" aria-label="Halaman sebelumnya"
                disabled={loading || page <= 1} onClick={() => onPageChange(page - 1)}><ChevronLeft aria-hidden="true" /></button>
            <button type="button" className="pagination-page" aria-label="Halaman berikutnya"
                disabled={loading || !hasData || page >= totalPages} onClick={() => onPageChange(page + 1)}><ChevronRight aria-hidden="true" /></button>
        </div>
    </nav>;
}
