import type { ReactNode } from "react";

interface SectionTitleProps {
    title: ReactNode;
    eyebrow?: ReactNode;
    meta?: ReactNode;
    aside?: ReactNode;
    page?: boolean;
    as?: "h1" | "h2" | "h3";
    className?: string;
}

export default function SectionTitle({ title, eyebrow, meta, aside, page, as: Heading = "h2", className }: SectionTitleProps) {
    return (
        <div className={`section-title${page ? " section-title--page" : ""}${className ? ` ${className}` : ""}`}>
            <div className="section-title__row">
                <div className="section-title__heading">
                    {eyebrow && <span className="section-title__eyebrow">{eyebrow}</span>}
                    <Heading className="section-title__text">{title}</Heading>
                </div>
                {aside && <span className="section-title__aside">{aside}</span>}
            </div>
            {meta && <p className="section-title__meta">{meta}</p>}
        </div>
    );
}
