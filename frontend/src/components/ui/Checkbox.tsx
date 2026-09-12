"use client";
import { Check } from "lucide-react";

interface CheckboxProps {
    checked: boolean;
    onChange: (checked: boolean) => void;
    label: React.ReactNode;
    color?: string;
    disabled?: boolean;
    className?: string;
}

export default function Checkbox({ checked, onChange, label, color, disabled, className }: CheckboxProps) {
    return (
        <label className={`group relative inline-flex min-h-[var(--control-height)] cursor-pointer select-none items-center gap-[var(--space-2)] text-xs font-[var(--weight-label)] text-[var(--secondary)] ${disabled ? "cursor-not-allowed opacity-45" : ""}${className ? ` ${className}` : ""}`} style={color ? { color } : undefined}>
            <input className="peer absolute m-0 h-px w-px opacity-0" type="checkbox" checked={checked} disabled={disabled} onChange={(event) => onChange(event.target.checked)} />
            <span className="grid h-[18px] w-[18px] flex-[0_0_18px] place-items-center rounded-[var(--radius-badge)] border-[1.5px] border-[var(--contour-strong)] bg-[var(--surface-raised)] transition-[background,border-color] duration-150 group-hover:border-[var(--selection)] peer-checked:border-[var(--brand)] peer-checked:bg-[var(--brand)] peer-focus-visible:outline-2 peer-focus-visible:outline-offset-2 peer-focus-visible:outline-[var(--selection)] [&>svg]:h-3 [&>svg]:w-3 [&>svg]:scale-60 [&>svg]:text-[var(--canvas)] [&>svg]:opacity-0 [&>svg]:transition-[opacity,transform] [&>svg]:duration-150 peer-checked:[&>svg]:scale-100 peer-checked:[&>svg]:opacity-100" aria-hidden="true"><Check /></span>
            <span className="inline-flex items-center gap-[var(--space-2)]">{label}</span>
        </label>
    );
}
