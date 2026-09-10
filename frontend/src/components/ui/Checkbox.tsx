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
        <label className={`ui-checkbox${disabled ? " is-disabled" : ""}${className ? ` ${className}` : ""}`} style={color ? { color } : undefined}>
            <input type="checkbox" checked={checked} disabled={disabled} onChange={(event) => onChange(event.target.checked)} />
            <span className="ui-checkbox-box" aria-hidden="true"><Check /></span>
            <span className="ui-checkbox-label">{label}</span>
        </label>
    );
}
