"use client";
import { useEffect, useId, useRef, useState } from "react";
import { Check, ChevronDown } from "lucide-react";
import { filterSelectOptions } from "@/utils/emissionAnalytics";

export interface SelectOption { value: string; label: string; disabled?: boolean }

interface SelectProps {
    value: string;
    options: SelectOption[];
    onChange: (value: string) => void;
    ariaLabel: string;
    placeholder?: string;
    className?: string;
    searchable?: boolean;
    searchPlaceholder?: string;
}

export default function Select({ value, options, onChange, ariaLabel, placeholder = "Pilih", className,
    searchable = false, searchPlaceholder = "Cari…" }: SelectProps) {
    const [open, setOpen] = useState(false);
    const [active, setActive] = useState(0);
    const [search, setSearch] = useState("");
    const rootRef = useRef<HTMLDivElement>(null);
    const searchRef = useRef<HTMLInputElement>(null);
    const listId = useId();
    const selected = options.find((option) => option.value === value);
    const visible = searchable ? filterSelectOptions(options, search) : options;
    const enabled = visible.filter((option) => !option.disabled);

    useEffect(() => {
        if (!open) return;
        if (searchable) searchRef.current?.focus();
        const closeOnOutside = (event: PointerEvent) => {
            if (!rootRef.current?.contains(event.target as Node)) setOpen(false);
        };
        document.addEventListener("pointerdown", closeOnOutside);
        return () => document.removeEventListener("pointerdown", closeOnOutside);
    }, [open, searchable]);

    function openList() {
        const index = visible.findIndex((option) => option.value === value);
        setActive(index >= 0 ? index : Math.max(0, visible.indexOf(enabled[0])));
        setOpen(true);
    }

    function closeList() {
        setOpen(false);
        setSearch("");
    }

    function move(delta: number) {
        if (!visible.length) return;
        let next = active;
        for (let i = 0; i < visible.length; i++) {
            next = (next + delta + visible.length) % visible.length;
            if (!visible[next].disabled) break;
        }
        setActive(next);
    }

    function commit(option: SelectOption) {
        if (option.disabled) return;
        onChange(option.value);
        closeList();
    }

    function onKeyDown(event: React.KeyboardEvent) {
        if (!open) {
            if (["ArrowDown", "ArrowUp", "Enter", " "].includes(event.key)) { event.preventDefault(); openList(); }
            return;
        }
        if (event.key === "ArrowDown" || event.key === "ArrowUp") {
            event.preventDefault();
            move(event.key === "ArrowDown" ? 1 : -1);
        } else if (event.key === "Home") { event.preventDefault(); setActive(visible.findIndex((option) => !option.disabled)); }
        else if (event.key === "End") { event.preventDefault(); setActive(visible.length - 1 - [...visible].reverse().findIndex((option) => !option.disabled)); }
        else if (event.key === "Enter") { event.preventDefault(); if (visible[active]) commit(visible[active]); }
        else if (event.key === " ") { event.preventDefault(); if (!searchable && visible[active]) commit(visible[active]); }
        else if (event.key === "Escape") { event.preventDefault(); if (searchable && search) setSearch(""); else closeList(); }
        else if (event.key === "Tab") { closeList(); }
    }

    function onSearchKeyDown(event: React.KeyboardEvent<HTMLInputElement>) {
        if (event.key === "ArrowDown" || event.key === "ArrowUp") {
            event.preventDefault();
            move(event.key === "ArrowDown" ? 1 : -1);
        } else if (event.key === "Enter") {
            event.preventDefault();
            if (visible[active]) commit(visible[active]);
        } else if (event.key === "Escape") {
            event.preventDefault();
            if (search) setSearch(""); else closeList();
        } else if (event.key === "Tab") {
            closeList();
        }
    }

    return (
        <div className={`relative w-full${className ? ` ${className}` : ""}`} ref={rootRef}>
            <button type="button" className="group flex min-h-[var(--control-height)] w-full cursor-pointer items-center justify-between gap-[var(--space-2)] rounded-[var(--radius-sm)] border border-[#334155] bg-[#102238] px-[var(--space-3)] text-left text-xs font-[var(--weight-label)] text-[#edf5ff] transition-colors duration-160 hover:border-[#4b6580] aria-expanded:border-[var(--green)]" role="combobox" aria-haspopup="listbox"
                aria-expanded={open} aria-controls={listId} aria-label={ariaLabel}
                onClick={() => (open ? closeList() : openList())} onKeyDown={onKeyDown}>
                <span className={`overflow-hidden text-ellipsis whitespace-nowrap ${selected ? "" : "text-[var(--muted)]"}`}>{selected?.label ?? placeholder}</span>
                <ChevronDown className="h-4 w-4 flex-[0_0_16px] text-[var(--secondary)] transition-transform duration-180 group-aria-expanded:rotate-180" aria-hidden="true" />
            </button>
            {open && (
                <div className="absolute inset-x-0 top-[calc(100%+6px)] z-20 max-h-[280px] overflow-y-auto rounded-[var(--radius-sm)] border border-[#334155] bg-[#0e1d2e] p-[var(--space-1)] shadow-[0_14px_34px_rgba(0,0,0,0.4)] animate-[select-in_0.14s_ease-out] motion-reduce:animate-none">
                    {searchable && (
                        <input ref={searchRef} className="sticky top-0 z-[1] mb-[var(--space-1)] w-full rounded-[5px] border border-[#1d3a5c] bg-[#0b1a2b] px-[var(--space-3)] py-[9px] text-xs text-[var(--text)] focus:outline-2 focus:-outline-offset-1 focus:outline-[var(--green)]" type="text" value={search}
                            placeholder={searchPlaceholder} aria-label={`Cari ${ariaLabel}`}
                            onChange={(event) => { setSearch(event.target.value); setActive(0); }}
                            onKeyDown={onSearchKeyDown} />
                    )}
                    <ul role="listbox" id={listId} aria-label={ariaLabel} className="m-0 list-none p-0">
                        {visible.map((option, index) => (
                            <li key={option.value} role="option" aria-selected={option.value === value} aria-disabled={option.disabled}>
                                <button type="button" tabIndex={-1} disabled={option.disabled}
                                    className={`flex w-full cursor-pointer items-center justify-between gap-[var(--space-2)] rounded-[5px] border-0 bg-transparent px-[var(--space-3)] py-[9px] text-left text-xs text-[var(--secondary)] disabled:cursor-default disabled:opacity-40 [&>svg]:h-3.5 [&>svg]:w-3.5 ${index === active ? "bg-[#14283c] text-[var(--text)]" : ""}${option.value === value ? " text-[var(--green)] font-[var(--weight-strong)]" : ""}`}
                                    onMouseEnter={() => !option.disabled && setActive(index)} onClick={() => commit(option)}>
                                    <span>{option.label}</span>
                                    {option.value === value && <Check aria-hidden="true" />}
                                </button>
                            </li>
                        ))}
                        {!visible.length && <li className="px-[var(--space-3)] py-[9px] text-xs text-[var(--muted)]">Tidak ada hasil</li>}
                    </ul>
                </div>
            )}
        </div>
    );
}
