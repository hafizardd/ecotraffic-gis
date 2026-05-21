'use client'

import dynamic from "next/dynamic";

const MapView = dynamic(() => import('@/components/Map/MapView'), {
  ssr: false,
  loading: () => <div>Loading map...</div>
})

export default function Home() {
  return (
    <main style={{ height: '100vh', margin: 0, padding: 0 }}>
      <MapView />
    </main>
  );
}
