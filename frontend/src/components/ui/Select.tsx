"use client";
import { useEffect, useId, useRef, useState } from "react";
import { Check, ChevronDown } from "lucide-react";

export interface SelectOption { value: string; label: string; disabled?: boolean }

interface SelectProps {
    value: string;
    options: SelectOption[];
    onChange: (value: string) => void;
    ariaLabel: string;
    placeholder?: string;
    className?: string;
}

export default function Select({ value, options, onChange, ariaLabel, placeholder = "Pilih", className }: SelectProps) {
    const [open, setOpen] = useState(false);
    const [active, setActive] = useState(0);
    const rootRef = useRef<HTMLDivElement>(null);
    const listId = useId();
    const selected = options.find((option) => option.value === value);
    const enabled = options.filter((option) => !option.disabled);

    useEffect(() => {
        if (!open) return;
        const closeOnOutside = (event: PointerEvent) => {
            if (!rootRef.current?.contains(event.target as Node)) setOpen(false);
        };
        document.addEventListener("pointerdown", closeOnOutside);
        return () => document.removeEventListener("pointerdown", closeOnOutside);
    }, [open]);

    function openList() {
        const index = options.findIndex((option) => option.value === value);
        setActive(index >= 0 ? index : Math.max(0, options.indexOf(enabled[0])));
        setOpen(true);
    }

    function commit(option: SelectOption) {
        if (option.disabled) return;
        onChange(option.value);
        setOpen(false);
    }

    function onKeyDown(event: React.KeyboardEvent) {
        if (!open) {
            if (["ArrowDown", "ArrowUp", "Enter", " "].includes(event.key)) { event.preventDefault(); openList(); }
            return;
        }
        if (event.key === "ArrowDown" || event.key === "ArrowUp") {
            event.preventDefault();
            const step = event.key === "ArrowDown" ? 1 : -1;
            let next = active;
            for (let i = 0; i < options.length; i++) {
                next = (next + step + options.length) % options.length;
                if (!options[next].disabled) break;
            }
            setActive(next);
        } else if (event.key === "Home") { event.preventDefault(); setActive(options.findIndex((option) => !option.disabled)); }
        else if (event.key === "End") { event.preventDefault(); setActive(options.length - 1 - [...options].reverse().findIndex((option) => !option.disabled)); }
        else if (event.key === "Enter" || event.key === " ") { event.preventDefault(); commit(options[active]); }
        else if (event.key === "Escape" || event.key === "Tab") { setOpen(false); }
    }

    return (
        <div className={`ui-select${className ? ` ${className}` : ""}`} ref={rootRef}>
            <button type="button" className="ui-select-trigger" role="combobox" aria-haspopup="listbox"
                aria-expanded={open} aria-controls={listId} aria-label={ariaLabel}
                onClick={() => (open ? setOpen(false) : openList())} onKeyDown={onKeyDown}>
                <span className={selected ? "ui-select-value" : "ui-select-value is-placeholder"}>{selected?.label ?? placeholder}</span>
                <ChevronDown className="ui-select-chevron" aria-hidden="true" />
            </button>
            {open && (
                <ul className="ui-select-menu" role="listbox" id={listId} aria-label={ariaLabel}>
                    {options.map((option, index) => (
                        <li key={option.value} role="option" aria-selected={option.value === value} aria-disabled={option.disabled}>
                            <button type="button" tabIndex={-1} disabled={option.disabled}
                                className={`ui-select-option${index === active ? " is-active" : ""}${option.value === value ? " is-selected" : ""}`}
                                onMouseEnter={() => !option.disabled && setActive(index)} onClick={() => commit(option)}>
                                <span>{option.label}</span>
                                {option.value === value && <Check aria-hidden="true" />}
                            </button>
                        </li>
                    ))}
                </ul>
            )}
        </div>
    );
}
