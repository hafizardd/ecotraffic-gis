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
        <label className={`group relative inline-flex min-h-(--control-height) cursor-pointer select-none items-center gap-(--space-2) text-xs font-(--weight-label) text-(--secondary) ${disabled ? "cursor-not-allowed opacity-45" : ""}${className ? ` ${className}` : ""}`} style={color ? { color } : undefined}>
            <input className="peer absolute m-0 h-px w-px opacity-0" type="checkbox" checked={checked} disabled={disabled} onChange={(event) => onChange(event.target.checked)} />
            <span className="grid h-4.5 w-4.5 flex-[0_0_18px] place-items-center rounded-(--radius-badge) border-[1.5px] border-(--contour-strong) bg-(--surface-raised) transition-[background,border-color] duration-150 group-hover:border-(--selection) peer-checked:border-(--brand) peer-checked:bg-(--brand) peer-focus-visible:outline-2 peer-focus-visible:outline-offset-2 peer-focus-visible:outline-(--selection) [&>svg]:h-3 [&>svg]:w-3 [&>svg]:scale-60 [&>svg]:text-(--canvas) [&>svg]:opacity-0 [&>svg]:transition-[opacity,transform] [&>svg]:duration-150 peer-checked:[&>svg]:scale-100 peer-checked:[&>svg]:opacity-100" aria-hidden="true"><Check /></span>
            <span className="inline-flex items-center gap-(--space-2)">{label}</span>
        </label>
    );
}
