import { Link } from "react-router-dom";
import { motion, useScroll, useTransform } from "framer-motion";
import { useRef } from "react";

/**
 * Footer — anchored by a massive Geist wordmark that sits below the link
 * grid and slowly parallaxes against scroll. Tiny links + SEBI disclaimer
 * fill the editorial bottom matter. No marketing CTA inside the footer
 * itself — the page-level CTA already lives in nav and pricing.
 */
export default function Footer({ onRequestAccess }) {
  const ref = useRef(null);
  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ["start end", "end end"],
  });
  const wordmarkY = useTransform(scrollYProgress, [0, 1], [40, -10]);

  return (
    <footer
      ref={ref}
      className="relative px-6 lg:px-12"
      style={{
        paddingTop: 80,
        paddingBottom: 56,
        borderTop: "1px solid var(--edge-1)",
        overflow: "hidden",
      }}
    >
      <div style={{ maxWidth: 1600, marginInline: "auto", position: "relative" }}>
        {/* Link grid */}
        <div className="grid grid-cols-2 md:grid-cols-4" style={{ gap: 40, marginBottom: 80 }}>
          <div className="md:col-span-2" style={{ maxWidth: 380 }}>
            <Link
              to="/"
              className="font-heading"
              style={{
                fontWeight: 600,
                fontSize: 18,
                letterSpacing: "-0.02em",
                color: "var(--text-1)",
              }}
            >
              NIFTYQUANT
            </Link>
            <p
              style={{
                color: "var(--text-2)",
                fontSize: 13,
                lineHeight: 1.6,
                marginTop: 14,
              }}
            >
              Pre-move detection for the Nifty 500. Built for serious Indian
              equity traders.
            </p>
          </div>

          <FooterColumn label="Product">
            <FooterLink to="/login">Sign in</FooterLink>
            <FooterLink onClick={onRequestAccess}>Request access</FooterLink>
          </FooterColumn>

          <FooterColumn label="Legal">
            <FooterLink href="mailto:access@niftyquant.com?subject=Privacy%20policy%20request">Privacy</FooterLink>
            <FooterLink href="mailto:access@niftyquant.com?subject=Terms%20of%20service%20request">Terms</FooterLink>
            <FooterLink href="mailto:access@niftyquant.com?subject=Risk%20disclosure%20request">Risk disclosure</FooterLink>
            <FooterLink href="mailto:access@niftyquant.com">Contact</FooterLink>
          </FooterColumn>
        </div>

        {/* Massive parallax wordmark */}
        <motion.div
          aria-hidden
          className="font-heading select-none"
          style={{
            y: wordmarkY,
            color: "var(--text-1)",
            opacity: 0.06,
            fontSize: "clamp(80px, 18vw, 280px)",
            fontWeight: 700,
            letterSpacing: "-0.05em",
            lineHeight: 0.85,
            marginBottom: 32,
            whiteSpace: "nowrap",
            overflow: "hidden",
          }}
        >
          NIFTYQUANT
        </motion.div>

        {/* SEBI disclaimer + copy */}
        <div style={{ borderTop: "1px solid var(--edge-1)", paddingTop: 28 }}>
          <p
            style={{
              fontSize: 11,
              lineHeight: 1.6,
              color: "var(--text-3)",
              maxWidth: 840,
              margin: 0,
            }}
          >
            Nifty Satvik is not a SEBI-registered investment advisor. Not investment
            advice. Past performance does not guarantee future returns. All
            trading involves risk; you could lose some or all of your capital.
            For educational and personal use only.
          </p>
          <p
            style={{
              fontSize: 11,
              color: "var(--text-4)",
              marginTop: 16,
              marginBottom: 0,
              fontFamily: "var(--font-mono, monospace)",
              letterSpacing: "0.04em",
            }}
          >
            © {new Date().getFullYear()} NIFTYQUANT · ALL RIGHTS RESERVED
          </p>
        </div>
      </div>
    </footer>
  );
}

function FooterColumn({ label, children }) {
  return (
    <div>
      <div
        className="font-mono uppercase"
        style={{
          fontSize: 10,
          letterSpacing: "0.18em",
          color: "var(--text-3)",
          marginBottom: 16,
        }}
      >
        {label}
      </div>
      <ul style={{ margin: 0, padding: 0, listStyle: "none", display: "flex", flexDirection: "column", gap: 10 }}>
        {children}
      </ul>
    </div>
  );
}

function FooterLink({ to, href, onClick, children }) {
  const style = {
    fontSize: 13,
    color: "var(--text-2)",
    textDecoration: "none",
    background: "none",
    border: "none",
    padding: 0,
    cursor: "pointer",
    transition: "color 180ms ease",
    textAlign: "left",
    display: "inline-block",
  };
  const onHover = (e) => (e.currentTarget.style.color = "var(--text-1)");
  const onLeave = (e) => (e.currentTarget.style.color = "var(--text-2)");

  if (to) {
    return (
      <li>
        <Link to={to} style={style} onMouseEnter={onHover} onMouseLeave={onLeave}>
          {children}
        </Link>
      </li>
    );
  }
  if (href) {
    return (
      <li>
        <a href={href} style={style} onMouseEnter={onHover} onMouseLeave={onLeave}>
          {children}
        </a>
      </li>
    );
  }
  return (
    <li>
      <button type="button" onClick={onClick} style={style} onMouseEnter={onHover} onMouseLeave={onLeave}>
        {children}
      </button>
    </li>
  );
}
