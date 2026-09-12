"use client";

import type { Ref } from "react";

export default function BangJoFab({ onOpen, buttonRef }: { onOpen: () => void; buttonRef?: Ref<HTMLButtonElement> }) {
    return (
        <button
            ref={buttonRef}
            type="button"
            className="bangjo-fab fixed right-[var(--bangjo-offset-right,22px)] bottom-[22px] z-40 grid h-[52px] w-[52px] cursor-pointer place-items-center rounded-full border border-[rgba(148,163,184,0.23)] bg-[rgba(7,20,34,0.9)] text-[#dce7f3] shadow-[0_8px_24px_rgba(0,0,0,0.28)] backdrop-blur-[8px] transition-[background,box-shadow] duration-180 hover:bg-[#102238] hover:shadow-[0_10px_30px_rgba(0,0,0,0.4)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-(--green) max-[760px]:right-[18px] max-[760px]:bottom-[18px] max-[760px]:h-11 max-[760px]:w-11"
            aria-label="Buka asisten Bang Jo"
            aria-expanded={false}
            onClick={onOpen}
        >
            <span className="flex flex-col gap-[3px] [&>i]:h-1 [&>i]:w-1 [&>i]:rounded-full [&>i:nth-child(1)]:bg-[#f87171] [&>i:nth-child(2)]:bg-[#fbbf24] [&>i:nth-child(3)]:bg-[#4ade80]" aria-hidden="true"><i /><i /><i /></span>
            <span className="absolute top-[3px] right-[3px] h-[7px] w-[7px] rounded-full bg-(--green) shadow-[0_0_0_4px_rgba(34,197,94,0.12)]" aria-hidden="true" />
        </button>
    );
}
