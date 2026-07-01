import { useRef } from "react";
import { motion, useInView } from "framer-motion";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { easeOutQuart } from "@/lib/motion";
import { GlowOrb } from "@/components/shared/GlowOrb";

const FAQS = [
  {
    q: "How does NiftyQuant work?",
    a: "A two-head LightGBM model scores every Nifty 500 stock daily on 79 features — technical, macro, sectoral. Signals that clear the confidence + return gates are routed through a risk manager (sector caps, regime filter, correlation filter), then sized via ATR-based risk budgeting. Every signal arrives with its entry, stop, and target precomputed.",
  },
  {
    q: "How do you prove the signals actually work?",
    a: "Three ways, in order of how much we trust them. Walk-forward backtests across 2010–2024 (out-of-sample, with brokerage and STT modelled in). A cost-realistic ₹10L paper ledger that trades the live signals the way a real, imperfect human would. And the one that can't be gamed — a live forward record that started on a fixed date and only grows. Past performance never guarantees future returns; we'd rather show the receipts than a headline number.",
  },
  {
    q: "Who is NiftyQuant for?",
    a: "Active swing traders on Indian equities — sophisticated retail to semi-professional. You should already understand position sizing and stop-loss discipline. We don't hand-hold beginners; we don't talk down to professionals.",
  },
  {
    q: "Do I need a Zerodha Kite API key?",
    a: "No. NiftyQuant runs on the founder's Kite Connect infrastructure. You only need a regular Zerodha trading account. To place orders through us, you connect your personal Kite in one OAuth step — and you can revoke it any time.",
  },
  {
    q: "Is my Kite session safe?",
    a: "Your access token is encrypted at rest with Fernet, scoped to your user account, and never shared. We don't store your Zerodha password. All traffic is TLS. Tokens expire daily at 6 AM IST per Zerodha's standard.",
  },
  {
    q: "How fresh is the data?",
    a: "Live market data and order book refresh every 18 seconds during market hours. Signals are scanned once at 4:15 PM IST every weekday. Backtest data and analytics are recomputed nightly.",
  },
  {
    q: "What are you building next?",
    a: "An AI sector-regime layer — a model that reads which sectors are setting up to lead and why, then grades its own calls against what the market actually does over the following weeks. It runs in shadow mode today and won't touch a live signal until it beats a fair baseline. We pre-register every research idea and kill the ones that don't hold up, before they ever reach you.",
  },
  {
    q: "How do I get access?",
    a: "Invite-only. Click Request access above; we onboard in small batches to keep latency low and support real.",
  },
];

export default function FAQ() {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, margin: "-80px" });

  return (
    <section
      className="relative px-6 lg:px-12 overflow-hidden"
      style={{ paddingTop: 120, paddingBottom: 120 }}
    >
      {/* Two soft orbs at opposite corners give the FAQ depth without
          competing with the body copy. Lower intensity than conversion
          sections (Hero / Pricing). */}
      <GlowOrb tone="brand" size={480} x="18%" y="20%" blur={140} style={{ zIndex: 0, opacity: 0.3 }} />
      <GlowOrb tone="info"  size={420} x="82%" y="85%" blur={130} style={{ zIndex: 0, opacity: 0.3 }} />

      <div className="relative" style={{ maxWidth: 880, marginInline: "auto", zIndex: 1 }} ref={ref}>
        <div className="mb-12">
          <div
            className="font-mono uppercase mb-3"
            style={{ fontSize: 11, letterSpacing: "0.18em", color: "var(--text-3)" }}
          >
            <span
              className="inline-block w-1.5 h-1.5 rounded-full align-middle mr-2"
              style={{ background: "var(--brand)" }}
            />
            08 · Questions
          </div>
          <motion.h2
            initial={{ opacity: 0, y: 14 }}
            animate={inView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.42, ease: easeOutQuart }}
            className="font-heading"
            style={{
              fontWeight: 600,
              color: "var(--text-1)",
              fontSize: "clamp(34px, 5vw, 64px)",
              lineHeight: 1.05,
              letterSpacing: "-0.025em",
              margin: 0,
            }}
          >
            What you'd ask before paying.
          </motion.h2>
        </div>

        <Accordion
          type="single"
          collapsible
          style={{ display: "flex", flexDirection: "column", gap: 8 }}
        >
          {FAQS.map((faq, i) => (
            <AccordionItem
              key={faq.q}
              value={`faq-${i}`}
              style={{
                background: "var(--surface-1)",
                border: "1px solid var(--edge-1)",
                borderRadius: "var(--r-card)",
                paddingInline: 20,
              }}
            >
              <AccordionTrigger
                className="font-heading hover:no-underline"
                style={{
                  fontWeight: 500,
                  color: "var(--text-1)",
                  fontSize: 15,
                  letterSpacing: "-0.005em",
                  paddingBlock: 18,
                  textAlign: "left",
                }}
              >
                {faq.q}
              </AccordionTrigger>
              <AccordionContent
                style={{
                  fontSize: 14,
                  lineHeight: 1.6,
                  color: "var(--text-2)",
                  paddingBottom: 18,
                }}
              >
                {faq.a}
              </AccordionContent>
            </AccordionItem>
          ))}
        </Accordion>
      </div>
    </section>
  );
}
