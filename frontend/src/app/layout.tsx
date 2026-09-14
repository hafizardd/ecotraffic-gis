import type { Metadata } from "next";
import "./globals.css";
import BrowserTelemetry from "@/components/BrowserTelemetry";

export const metadata: Metadata = {
  title: "EcoTraffic GIS",
  description: "AI-Based Decision Support System for Sustainable Public Transport Development via Transport Emission Analysis in Yogyakarta City",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="id">
      <body><BrowserTelemetry />{children}</body>
    </html>
  );
}
