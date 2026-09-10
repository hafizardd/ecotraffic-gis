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
        <div className={`ui-select${className ? ` ${className}` : ""}`} ref={rootRef}>
            <button type="button" className="ui-select-trigger" role="combobox" aria-haspopup="listbox"
                aria-expanded={open} aria-controls={listId} aria-label={ariaLabel}
                onClick={() => (open ? closeList() : openList())} onKeyDown={onKeyDown}>
                <span className={selected ? "ui-select-value" : "ui-select-value is-placeholder"}>{selected?.label ?? placeholder}</span>
                <ChevronDown className="ui-select-chevron" aria-hidden="true" />
            </button>
            {open && (
                <div className="ui-select-menu">
                    {searchable && (
                        <input ref={searchRef} className="ui-select-search" type="text" value={search}
                            placeholder={searchPlaceholder} aria-label={`Cari ${ariaLabel}`}
                            onChange={(event) => { setSearch(event.target.value); setActive(0); }}
                            onKeyDown={onSearchKeyDown} />
                    )}
                    <ul role="listbox" id={listId} aria-label={ariaLabel} className="ui-select-list">
                        {visible.map((option, index) => (
                            <li key={option.value} role="option" aria-selected={option.value === value} aria-disabled={option.disabled}>
                                <button type="button" tabIndex={-1} disabled={option.disabled}
                                    className={`ui-select-option${index === active ? " is-active" : ""}${option.value === value ? " is-selected" : ""}`}
                                    onMouseEnter={() => !option.disabled && setActive(index)} onClick={() => commit(option)}>
                                    <span>{option.label}</span>
                                    {option.value === value && <Check aria-hidden="true" />}
                                </button>
                            </li>
                        ))}
                        {!visible.length && <li className="ui-select-empty">Tidak ada hasil</li>}
                    </ul>
                </div>
            )}
        </div>
    );
}
