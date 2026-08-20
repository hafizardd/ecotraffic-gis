'use client'

import dynamic from "next/dynamic";
import { EmissionsProvider } from "@/context/EmissionsContext";
import DashboardShell from "@/components/Dashboard/DashboardShell";

const MapView = dynamic(() => import('@/components/Map/MapView'), {
  ssr: false,
  loading: () => <div className="map-state"><span className="loading-spinner" />Memuat peta...</div>
})

export default function Home() {
  return (
    <EmissionsProvider>
      <DashboardShell><MapView /></DashboardShell>
    </EmissionsProvider>
  );
}
