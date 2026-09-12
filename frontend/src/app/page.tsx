'use client'

import dynamic from "next/dynamic";
import { EmissionsProvider } from "@/context/EmissionsContext";
import DashboardShell from "@/components/Dashboard/DashboardShell";
import Skeleton from "@/components/ui/Skeleton";

const MapView = dynamic(() => import('@/components/Map/MapView'), {
  ssr: false,
  loading: () => <div className="flex h-full min-h-0 w-full gap-3"><div className="relative h-full min-w-0 flex-1 overflow-hidden rounded-xl border border-(--border) bg-(--card) shadow-[0_16px_40px_rgba(0,0,0,0.18)]"><Skeleton height="100%" width="100%" radius={12} /></div></div>
})

export default function Home() {
  return (
    <EmissionsProvider>
      <DashboardShell><MapView /></DashboardShell>
    </EmissionsProvider>
  );
}
