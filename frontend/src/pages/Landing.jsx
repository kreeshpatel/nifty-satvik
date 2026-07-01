import { useState } from "react";
import { RegimeProvider } from "@/context/RegimeContext";
import LenisProvider from "@/components/landing/LenisProvider";
import ScrollProgress from "@/components/landing/ScrollProgress";
import CursorGrid from "@/components/landing/CursorGrid";
// LiveTicker (auto-scrolling stock marquee) deliberately removed — it was
// adding visual motion noise without conveying meaningful signal context.
import Navigation from "@/components/landing/Navigation";
import IntroChoreography from "@/components/landing/IntroChoreography";
import HeroV3 from "@/components/landing/HeroV3";
import AssetClassStrip from "@/components/landing/AssetClassStrip";
import CalendarHeatmap from "@/components/landing/CalendarHeatmap";
import Features from "@/components/landing/Features";
import HowSignalsWork from "@/components/landing/HowSignalsWork";
// EquityCurve dropped from landing — it pulls in EquityShaderOverlay which
// instantiates a THREE.Clock + custom shader on a rAF loop. With the new
// dashboard mockup already covering the "see the data" job in the hero,
// it's redundant and was starving the main thread to ~3fps on this page.
import PricingSection from "@/components/landing/PricingSection";
import FounderSection from "@/components/landing/FounderSection";
import FAQ from "@/components/landing/FAQ";
import Footer from "@/components/landing/Footer";
import RequestAccessModal from "@/components/landing/RequestAccessModal";
import ZoomLock from "@/components/landing/ZoomLock";
import "@/styles/landing.css";

/**
 * Landing — fxreplay.com-inspired composition.
 *
 * Hero → asset class strip → features → how-it-works → calendar
 * heatmap → equity curve → pricing → founder → FAQ → footer.
 *
 * Notable deprecations from the previous landing (kept on disk for
 * reference but no longer rendered):
 *   - Hero (replaced by HeroV3)
 *   - SampleSignal (folded into HeroV3's dashboard mockup)
 *   - MarketConstellation (WebGL R3F sphere — too heavy, replaced by
 *     the static dashboard mockup in the hero)
 *   - SectorHeatmapPinned (replaced by CalendarHeatmap)
 *   - LiveStats, RegimeStatement (over-decorative, dropped)
 */

function LandingShell() {
  const [requestOpen, setRequestOpen] = useState(false);

  return (
    <LenisProvider>
      <ZoomLock />
      <div
        data-page-ctx="landing"
        className="relative min-h-screen font-sans"
        style={{
          background: "var(--surface-0)",
          color: "var(--text-1)",
          "--text-1": "#F1F5FF",
          "--text-2": "#B8C0DA",
          "--text-3": "#7A82A5",
        }}
      >
        <IntroChoreography />
        <ScrollProgress />
        <CursorGrid enabled />
        <Navigation />

        <HeroV3 onRequestAccess={() => setRequestOpen(true)} />
        <AssetClassStrip />
        <Features />
        <HowSignalsWork />
        <CalendarHeatmap />
        <PricingSection onRequestAccess={() => setRequestOpen(true)} />
        <FounderSection />
        <FAQ />
        <Footer onRequestAccess={() => setRequestOpen(true)} />

        <RequestAccessModal open={requestOpen} onOpenChange={setRequestOpen} />
      </div>
    </LenisProvider>
  );
}

export default function Landing() {
  return (
    <RegimeProvider>
      <LandingShell />
    </RegimeProvider>
  );
}
