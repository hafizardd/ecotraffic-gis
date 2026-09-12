"use client";

import ReactMarkdown from "react-markdown";

// Only http(s) links survive; javascript:/data: become inert.
const SAFE_URL = /^https?:\/\//i;

// Deliberately restrictive: no headings, tables, images, or raw HTML. Raw HTML
// is never executed because rehype-raw is not used, and skipHtml drops it.
const ALLOWED_ELEMENTS = ["p", "strong", "em", "ul", "ol", "li", "br", "code", "a"];

export default function MarkdownText({ children, className }: { children: string; className?: string }) {
    return (
        <div className={className ? `bangjo-markdown ${className}` : "bangjo-markdown"}>
            <ReactMarkdown
                allowedElements={ALLOWED_ELEMENTS}
                unwrapDisallowed
                skipHtml
                urlTransform={(url) => (SAFE_URL.test(url) ? url : "")}
            >
                {children}
            </ReactMarkdown>
        </div>
    );
}
