"use client";

import { useState } from "react";
import { ChevronDown, ChevronUp, Info } from "lucide-react";
import { CAMERA_TIER_COLORS, FIVE_TIER_COLORS, interventionGradientCss, MAP_MODES, type MapLayerKey, type MapMode } from "@/constants/mapColors";

interface MapLegendProps {
    onCameraSelect: (cameraId: string) => void;
    availableCameraIds: string[];
    mode: MapMode;
    segmentBuckets: { color: string; label: string }[];
    cameraHistorical?: number;
    cameraTotal: number;
    layerVisibility: Record<MapLayerKey, boolean>;
}

export default function MapLegend({ onCameraSelect, availableCameraIds, mode, segmentBuckets, cameraHistorical = 0, cameraTotal, layerVisibility }: MapLegendProps) {
    const [open, setOpen] = useState(false);
    const modeLabel = MAP_MODES.find((item) => item.key === mode)?.label ?? "";

    return (
        <aside className={`absolute left-3 z-19 flex max-h-[calc(100%-156px)] flex-col overflow-hidden rounded-md border border-(--contour-strong) bg-[rgba(11,32,41,0.94)] text-[11px] text-(--text) shadow-(--shadow-float) backdrop-blur-[10px] max-[760px]:left-2 max-[760px]:max-h-[48vh] ${mode === "potential" ? "bottom-3 max-[760px]:bottom-28" : "bottom-3 max-[760px]:bottom-2"} ${open ? "w-62 max-[760px]:right-2 max-[760px]:w-auto" : "w-auto max-w-55"}`} aria-label="Legenda peta">
            <button type="button" className="flex min-h-10 w-full cursor-pointer items-center gap-2 border-0 bg-transparent px-3 text-left text-[11px] font-semibold text-(--text) transition-colors hover:bg-(--surface) max-[760px]:min-h-11 [&>svg]:h-4 [&>svg]:w-4 [&>svg]:flex-[0_0_16px] [&>span]:flex-1" onClick={() => setOpen((value) => !value)} aria-expanded={open} aria-controls="map-legend-content">
                <Info className="text-(--selection)" aria-hidden="true" />
                <span>Legenda · {modeLabel}</span>
                {open ? <ChevronUp aria-hidden="true" /> : <ChevronDown aria-hidden="true" />}
            </button>
            {open && (
                <div id="map-legend-content" className="flex flex-col gap-3 overflow-y-auto border-t border-(--border) px-3 pt-2 pb-3 [&_h3]:my-[5px_0_7px] [&_h3]:text-[10px] [&_h3]:font-bold [&_h3]:tracking-widest [&_h3]:text-(--muted) [&_h3]:uppercase">
                    {mode === "traffic" && (
                        <>
                            {layerVisibility.segments && <section>
                                <h3>Emisi segmen (g/jam)</h3>
                                <ul className="m-0 flex list-none flex-col gap-1.5 p-0 [&_li]:flex [&_li]:items-center [&_li]:gap-2 [&_li]:text-[11px] [&_li]:text-(--secondary) [&_i]:h-2.5 [&_i]:w-2.5 [&_i]:flex-[0_0_10px] [&_i]:rounded-(--radius-badge)">{segmentBuckets.map((bucket) => <li key={bucket.label}><i style={{ background: bucket.color }} />{bucket.label}</li>)}</ul>
                            </section>}
                            {layerVisibility.cameras && <><section>
                                <h3>CCTV: emisi CO₂ (g/min)</h3>
                                <ul className="m-0 flex list-none flex-col gap-1.5 p-0 [&_li]:flex [&_li]:items-center [&_li]:gap-2 [&_li]:text-[11px] [&_li]:text-(--secondary) [&_i]:h-2.5 [&_i]:w-2.5 [&_i]:flex-[0_0_10px] [&_i]:rounded-(--radius-badge)">
                                    <li><i style={{ background: CAMERA_TIER_COLORS.low }} />&lt; 500</li>
                                    <li><i style={{ background: CAMERA_TIER_COLORS.medium }} />500–1.500</li>
                                    <li><i style={{ background: CAMERA_TIER_COLORS.high }} />&gt; 1.500</li>
                                    <li><i style={{ background: CAMERA_TIER_COLORS.unavailable }} />Tanpa data</li>
                                    <li><i style={{ background: "#38bdf8" }} />Data statis</li>
                                </ul>
                                <p className="mt-2 mb-0 text-[10px] leading-4 text-(--muted)">{cameraTotal} kamera{cameraHistorical > 0 ? ` · ${cameraHistorical} data statis` : ""}</p>
                            </section>
                            <section>
                                <h3>Ketersediaan video CCTV</h3>
                                <p className="m-0 text-[11px] font-semibold text-(--text)">2 kamera tersedia untuk pemantauan:</p>
                                <ul className="mt-1 mb-2 list-disc space-y-1 pl-4 text-[11px] leading-4 text-(--secondary)">
                                    {[
                                        { id: "atcs_jlagran", name: "Simpang Jlagran (PTZ)" },
                                        { id: "atcs_balaikota_timur", name: "Simpang Balaikota View Timur" },
                                    ].map(camera => <li key={camera.id}>
                                        <button type="button" disabled={!availableCameraIds.includes(camera.id)}
                                            onClick={event => { event.stopPropagation(); onCameraSelect(camera.id); }}
                                            className="min-h-9 cursor-pointer text-left text-(--selection) underline underline-offset-4 hover:text-(--text) focus-visible:outline-2 focus-visible:outline-offset-2 disabled:cursor-wait disabled:opacity-50"
                                            aria-label={`Lihat lokasi dan video ${camera.name}`}>
                                            {camera.name}
                                        </button>
                                    </li>)}
                                </ul>
                                <p className="mt-0 mb-2 text-[10px] leading-4 text-(--muted)">Klik nama kamera untuk menuju titik dan membuka panel video.</p>
                                <div className="mb-3 flex flex-col gap-2">
                                    <div className="flex items-center gap-2">
                                        <svg aria-hidden="true" viewBox="0 0 48 48" className="h-10 w-10 shrink-0">
                                            <path d="M4 16H44M16 4V44M4 32H44M32 4V44" stroke="#64748b" strokeWidth="2" />
                                            <circle cx="24" cy="24" r="15" fill="#ef4444" fillOpacity="0.45" stroke="white" strokeWidth="2.5" />
                                        </svg>
                                        <span>Video tersedia: titik tanpa cincin biru, dapat terlihat transparan.</span>
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <svg aria-hidden="true" viewBox="0 0 48 48" className="h-10 w-10 shrink-0">
                                            <circle cx="24" cy="24" r="21" fill="none" stroke="#38bdf8" strokeWidth="2" />
                                            <circle cx="24" cy="24" r="16" fill="#ef4444" stroke="#38bdf8" strokeWidth="2.5" />
                                        </svg>
                                        <span>Video belum tersedia: dua lingkaran biru (data statis).</span>
                                    </div>
                                </div>
                                <p className="m-0 text-[11px] leading-4 text-(--secondary)">Titik CCTV lainnya: video belum tersedia dalam aplikasi karena keterbatasan resource saat ini.</p>
                                <p className="mt-2 mb-0 text-[10px] leading-4 text-(--muted)">Warna isi menunjukkan emisi; transparansi mengikuti kesegaran data. Simbol di atas menggambarkan kondisi demo saat ini, bukan jaminan koneksi kamera.</p>
                            </section>
                            </>}
                        </>
                    )}
                    {mode === "potential" && (
                        <>
                            {layerVisibility.activityGrid && <section>
                                <h3>Potensi aktivitas</h3>
                                <ul className="m-0 flex list-none flex-col gap-1.5 p-0 [&_li]:flex [&_li]:items-center [&_li]:gap-2 [&_li]:text-[11px] [&_li]:text-(--secondary) [&_i]:h-2.5 [&_i]:w-2.5 [&_i]:flex-[0_0_10px] [&_i]:rounded-(--radius-badge)">
                                    <li><i style={{ background: FIVE_TIER_COLORS.veryLow }} />Sangat Rendah</li>
                                    <li><i style={{ background: FIVE_TIER_COLORS.low }} />Rendah</li>
                                    <li><i style={{ background: FIVE_TIER_COLORS.medium }} />Sedang</li>
                                    <li><i style={{ background: FIVE_TIER_COLORS.high }} />Tinggi</li>
                                    <li><i style={{ background: FIVE_TIER_COLORS.veryHigh }} />Sangat Tinggi</li>
                                    <li><i style={{ background: FIVE_TIER_COLORS.unknown }} />Tanpa data</li>
                                </ul>
                                <p className="mt-2 mb-0 text-[10px] leading-4 text-(--muted)">Warna mengikuti klasifikasi potensi sel, sama dengan panel detail. Hexagon mengikuti zoom.</p>
                            </section>}
                            {layerVisibility.surveyStops && <section>
                                <h3>Kondisi halte (skor intervensi)</h3>
                                <div className="flex flex-col gap-1">
                                    <div className="h-2.5 rounded-(--radius-badge)" style={{ background: interventionGradientCss() }} />
                                    <div className="flex justify-between text-[10px] text-(--muted)"><span>Prioritas</span><span>Baik</span></div>
                                </div>
                                <p className="mt-2 mb-0 text-[10px] leading-4 text-(--muted)">Skor rendah = prioritas intervensi. Klik halte untuk radius 500 m.</p>
                            </section>}
                        </>
                    )}
                </div>
            )}
        </aside>
    );
}
