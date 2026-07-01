import { useState, useEffect, useContext } from "react";
import { Link, useLocation } from "react-router-dom";
import { ArrowUpRight } from "lucide-react";
import { AuthContext } from "@/context/AuthContext";

export default function Navigation() {
  const [scrolled, setScrolled] = useState(false);
  const location = useLocation();
  const { user } = useContext(AuthContext);
  const isLogin = location.pathname === "/login";

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener("scroll", onScroll);
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  if (isLogin) return null;

  return (
    <nav
      className="fixed left-0 right-0 z-50"
      style={{
        top: "calc(36px + env(safe-area-inset-top))",
        transition: "background 220ms ease, border-color 220ms ease, backdrop-filter 220ms ease",
        background: scrolled ? "rgba(0,0,0,0.72)" : "transparent",
        borderBottom: scrolled ? "1px solid var(--edge-1)" : "1px solid transparent",
        backdropFilter: scrolled ? "blur(14px) saturate(140%)" : "none",
        WebkitBackdropFilter: scrolled ? "blur(14px) saturate(140%)" : "none",
      }}
    >
      <div
        className="mx-auto flex items-center justify-between"
        style={{
          maxWidth: 1600,
          paddingInline: 16,
          height: 56,
        }}
      >
        <Link
          to="/"
          className="font-heading"
          style={{
            fontWeight: 600,
            fontSize: 17,
            letterSpacing: "-0.02em",
            color: "var(--text-1)",
          }}
        >
          NIFTYQUANT
        </Link>

        <div className="flex items-center" style={{ gap: 18 }}>
          <Link
            to={user ? "/dashboard" : "/login"}
            className="hidden sm:inline-block transition-opacity"
            style={{
              fontSize: 13,
              color: "var(--text-2)",
              letterSpacing: "-0.005em",
            }}
          >
            {user ? "Dashboard" : "Sign in"}
          </Link>
          <Link
            to={user ? "/dashboard" : "/login"}
            className="inline-flex items-center gap-1.5 transition-opacity"
            style={{
              height: 34,
              paddingInline: 14,
              background: "var(--brand)",
              color: "var(--brand-fg)",
              borderRadius: "var(--r-chip)",
              fontSize: 13,
              fontWeight: 600,
              letterSpacing: "-0.005em",
            }}
          >
            {user ? "Open dashboard" : "Request access"}
            <ArrowUpRight size={13} strokeWidth={2.4} />
          </Link>
        </div>
      </div>
    </nav>
  );
}
