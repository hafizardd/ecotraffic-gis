'use client'

import dynamic from "next/dynamic";
import { EmissionsProvider } from "@/context/EmissionsContext";
import DashboardShell from "@/components/Dashboard/DashboardShell";
import Skeleton from "@/components/ui/Skeleton";

const MapView = dynamic(() => import('@/components/Map/MapView'), {
  ssr: false,
  loading: () => <div className="map-panel-layout"><div className="map-area"><Skeleton height="100%" width="100%" radius={12} /></div></div>
})

export default function Home() {
  return (
    <EmissionsProvider>
      <DashboardShell><MapView /></DashboardShell>
    </EmissionsProvider>
  );
}
