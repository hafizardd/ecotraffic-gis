"use client";

import { useEffect, useRef, useState } from "react";
import { Check, Layers3, Moon, Sun } from "lucide-react";

import {
    LAYER_LABELS,
    MAP_MODES,
    MODE_VISIBILITY,
    type MapLayerKey,
    type MapMode,
} from "@/constants/mapColors";

type BasemapStyle = "street-2d-building" | "dark";

interface MapControlDeckProps {
    mode: MapMode;
    onModeChange: (mode: MapMode) => void;
    basemap: BasemapStyle;
    onBasemapChange: (style: BasemapStyle) => void;
    layerVisibility: Record<MapLayerKey, boolean>;
    onLayerVisibilityChange: (layer: MapLayerKey, visible: boolean) => void;
}

const LAYER_KEYS = Object.keys(LAYER_LABELS) as MapLayerKey[];

export default function MapControlDeck({
    mode,
    onModeChange,
    basemap,
    onBasemapChange,
    layerVisibility,
    onLayerVisibilityChange,
}: MapControlDeckProps) {
    const [layersOpen, setLayersOpen] = useState(false);
    const layerRootRef = useRef<HTMLDivElement>(null);
    const layerTriggerRef = useRef<HTMLButtonElement>(null);
    const layerMenuRef = useRef<HTMLDivElement>(null);
    const modeTabRefs = useRef<Partial<Record<MapMode, HTMLButtonElement | null>>>({});
    const modeLayers = LAYER_KEYS.filter((key) => MODE_VISIBILITY[mode][key]);
    const activeCount = modeLayers.filter((key) => layerVisibility[key]).length;
    const isDark = basemap === "dark";

    useEffect(() => {
        if (!layersOpen) return;
        window.requestAnimationFrame(() => layerMenuRef.current?.querySelector<HTMLElement>('button:not([disabled])')?.focus());
        const close = (event: PointerEvent) => {
            if (!layerRootRef.current?.contains(event.target as Node)) setLayersOpen(false);
        };
        const closeOnEscape = (event: KeyboardEvent) => {
            if (event.key === "Escape") {
                event.preventDefault();
                setLayersOpen(false);
                layerTriggerRef.current?.focus();
            }
        };
        document.addEventListener("pointerdown", close);
        document.addEventListener("keydown", closeOnEscape);
        return () => {
            document.removeEventListener("pointerdown", close);
            document.removeEventListener("keydown", closeOnEscape);
        };
    }, [layersOpen]);

    const selectModeFromKeyboard = (event: React.KeyboardEvent<HTMLButtonElement>, key: MapMode) => {
        const index = MAP_MODES.findIndex((item) => item.key === key);
        let next = index;
        if (event.key === "ArrowRight") next = (index + 1) % MAP_MODES.length;
        else if (event.key === "ArrowLeft") next = (index - 1 + MAP_MODES.length) % MAP_MODES.length;
        else if (event.key === "Home") next = 0;
        else if (event.key === "End") next = MAP_MODES.length - 1;
        else return;
        event.preventDefault();
        const nextMode = MAP_MODES[next].key;
        onModeChange(nextMode);
        modeTabRefs.current[nextMode]?.focus();
    };

    return (
        <div className="absolute top-3 left-3 z-20 flex max-w-[calc(100%-24px)] items-center gap-1.5 rounded-md border border-(--contour-strong) bg-[rgba(11,32,41,0.94)] p-1.5 shadow-(--shadow-float) backdrop-blur-[10px] max-[760px]:top-2 max-[760px]:right-2 max-[760px]:left-2 max-[760px]:max-w-none">
            <div className="inline-flex min-w-0 items-center rounded-sm bg-[rgba(9,26,34,0.72)] p-0.5" role="tablist" aria-label="Mode peta">
                {MAP_MODES.map(({ key, label }) => (
                    <button
                        key={key}
                        type="button"
                        role="tab"
                        aria-selected={mode === key}
                        tabIndex={mode === key ? 0 : -1}
                        ref={(node) => { modeTabRefs.current[key] = node; }}
                        className={`relative min-h-9 cursor-pointer whitespace-nowrap rounded-[5px] border border-transparent px-3 text-[11px] font-semibold transition-[border-color,background,color] duration-150 max-[760px]:min-h-11 max-[430px]:px-2.5 ${mode === key ? "border-[rgba(56,189,248,0.32)] bg-(--selection-soft) text-[#8edcff]" : "text-(--text-muted) hover:bg-(--surface) hover:text-(--text)"}`}
                        onClick={() => onModeChange(key)}
                        onKeyDown={(event) => selectModeFromKeyboard(event, key)}
                    >
                        {label}
                    </button>
                ))}
            </div>

            <span className="h-6 border-l border-(--border)" aria-hidden="true" />

            <button
                type="button"
                className="flex min-h-9 cursor-pointer items-center gap-2 rounded-sm border border-transparent bg-transparent px-2.5 text-[11px] font-semibold text-(--text-muted) transition-colors hover:border-(--border) hover:bg-(--surface) hover:text-(--text) max-[760px]:min-h-11 max-[560px]:w-11 max-[560px]:justify-center max-[560px]:px-0 [&>svg]:h-4 [&>svg]:w-4"
                aria-label={isDark ? "Gunakan basemap jalan terang" : "Gunakan basemap jalan gelap"}
                title={isDark ? "Basemap jalan terang" : "Basemap jalan gelap"}
                onClick={() => onBasemapChange(isDark ? "street-2d-building" : "dark")}
            >
                {isDark ? <Sun aria-hidden="true" /> : <Moon aria-hidden="true" />}
                <span className="max-[560px]:sr-only">{isDark ? "Peta terang" : "Peta gelap"}</span>
            </button>

            <div className="relative" ref={layerRootRef}>
                <button
                    ref={layerTriggerRef}
                    type="button"
                    className="flex min-h-9 cursor-pointer items-center gap-2 rounded-sm border border-transparent bg-transparent px-2.5 text-[11px] font-semibold text-(--text-muted) transition-colors hover:border-(--border) hover:bg-(--surface) hover:text-(--text) max-[760px]:min-h-11 max-[560px]:w-11 max-[560px]:justify-center max-[560px]:px-0 [&>svg]:h-4 [&>svg]:w-4"
                    aria-expanded={layersOpen}
                    aria-controls="map-layer-menu"
                    aria-label={`Atur layer peta, ${activeCount} dari ${modeLayers.length} aktif`}
                    title="Atur layer peta"
                    onClick={() => setLayersOpen((value) => !value)}
                >
                    <Layers3 aria-hidden="true" />
                    <span className="max-[560px]:sr-only">Layer</span>
                    <span className="rounded-(--radius-badge) bg-(--surface-raised) px-1.5 py-0.5 font-(family-name:--font-data) text-[10px] text-(--secondary) max-[560px]:hidden">{activeCount}/{modeLayers.length}</span>
                </button>

                {layersOpen && (
                    <div ref={layerMenuRef} id="map-layer-menu" className="absolute top-[calc(100%+10px)] right-0 w-[260px] rounded-md border border-(--contour-strong) bg-[rgba(11,32,41,0.97)] p-2 shadow-(--shadow-float) backdrop-blur-[12px] animate-[select-in_0.14s_ease-out] motion-reduce:animate-none" role="group" aria-label="Layer pada mode aktif">
                        <div className="border-b border-(--border) px-2 pt-1 pb-2">
                            <strong className="block text-[11px] font-semibold">Layer · {MAP_MODES.find((item) => item.key === mode)?.label}</strong>
                            <span className="mt-0.5 block text-[10px] text-(--muted)">Tampilkan hanya informasi yang dibutuhkan.</span>
                        </div>
                        <div className="grid gap-1 pt-2">
                            {modeLayers.map((key) => {
                                const checked = layerVisibility[key];
                                return (
                                    <button
                                        key={key}
                                        type="button"
                                        role="switch"
                                        aria-checked={checked}
                                        className="flex min-h-10 w-full cursor-pointer items-center gap-2.5 rounded-sm border border-transparent bg-transparent px-2 text-left text-[12px] text-(--secondary) transition-colors hover:border-(--border) hover:bg-(--surface) hover:text-(--text)"
                                        onClick={() => onLayerVisibilityChange(key, !checked)}
                                    >
                                        <span className={`grid h-[18px] w-[18px] flex-[0_0_18px] place-items-center rounded-(--radius-badge) border transition-colors [&>svg]:h-3 [&>svg]:w-3 ${checked ? "border-(--selection) bg-(--selection) text-[#06202b]" : "border-(--contour-strong) bg-(--surface-raised) text-transparent"}`} aria-hidden="true"><Check /></span>
                                        <span className="flex-1">{LAYER_LABELS[key]}</span>
                                        <span className={`text-[10px] ${checked ? "text-[#8edcff]" : "text-(--muted)"}`}>{checked ? "Aktif" : "Nonaktif"}</span>
                                    </button>
                                );
                            })}
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
