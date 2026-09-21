"use client";

import ReactMarkdown from "react-markdown";

// Only http(s) links survive; javascript:/data: become inert.
const SAFE_URL = /^https?:\/\//i;

// Deliberately restrictive: no headings, images, or raw HTML. Tables are
// allowed for compact comparisons; raw HTML is never executed because
// rehype-raw is not used, and skipHtml drops it.
const ALLOWED_ELEMENTS = [
    "p", "strong", "em", "ul", "ol", "li", "br", "code", "a",
    "table", "thead", "tbody", "tr", "th", "td",
];

export default function MarkdownText({ children, className }: { children: string; className?: string }) {
    return (
        <div className={`block [&>p]:mt-0 [&>p]:mb-1.5 [&>:last-child]:mb-0 [&>ul]:mt-0 [&>ul]:mb-1.5 [&>ul]:pl-4 [&>ol]:mt-0 [&>ol]:mb-1.5 [&>ol]:pl-4 [&_li]:my-0.5 [&_strong]:font-semibold [&_strong]:text-[#e2eefb] [&_code]:rounded [&_code]:bg-[#102238] [&_code]:px-1 [&_code]:py-px [&_code]:font-mono [&_code]:text-[10px] [&_a]:text-(--tsp) [&_table]:block [&_table]:w-full [&_table]:overflow-x-auto [&_table]:border-collapse [&_table]:text-[10px] [&_th]:border [&_th]:border-(--border) [&_th]:px-2 [&_th]:py-1 [&_th]:text-left [&_th]:font-semibold [&_td]:border [&_td]:border-(--border) [&_td]:px-2 [&_td]:py-1${className ? ` ${className}` : ""}`}>
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
