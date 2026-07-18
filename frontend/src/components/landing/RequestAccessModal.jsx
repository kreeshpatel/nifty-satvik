import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Loader2, CheckCircle2 } from "lucide-react";

const API = process.env.REACT_APP_API_URL ?? '';

export default function RequestAccessModal({ open, onOpenChange }) {
  const [formData, setFormData] = useState({
    name: "",
    email: "",
    trading_experience: "",
    message: "",
  });
  const [loading, setLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!formData.name || !formData.email) return;
    setLoading(true);
    setError("");
    try {
      const res = await fetch(`${API}/api/access-requests`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(formData),
      });
      // Read as text first to dodge "body stream already read" issue
      const text = await res.text();
      let data = {};
      try {
        data = text ? JSON.parse(text) : {};
      } catch {
        data = {};
      }
      if (res.ok) {
        setSubmitted(true);
      } else {
        setError(data.detail || "Something went wrong. Please try again.");
      }
    } catch {
      setError("Network error. Please try again.");
    }
    setLoading(false);
  };

  const handleClose = (val) => {
    onOpenChange(val);
    if (!val) {
      setTimeout(() => {
        setSubmitted(false);
        setError("");
        setFormData({ name: "", email: "", trading_experience: "", message: "" });
      }, 300);
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent
        srTitle="Request access to Nifty Satvik"
        className="text-white w-[calc(100vw-32px)] max-w-md max-h-[90dvh] overflow-y-auto"
        style={{
          background: "var(--surface-1)",
          borderColor: "var(--edge-1)",
        }}
      >
        {submitted ? (
          <div className="text-center py-6">
            <CheckCircle2 className="w-12 h-12 text-[color:var(--bull)] mx-auto mb-4" />
            <DialogTitle className="font-heading font-bold text-xl text-white mb-2">
              Request submitted
            </DialogTitle>
            <DialogDescription className="text-sm text-[color:var(--text-2)]">
              We'll review your request and get back to you within 24-48 hours.
            </DialogDescription>
          </div>
        ) : (
          <>
            <DialogHeader>
              <DialogTitle className="font-heading font-bold text-xl text-white">
                Request access
              </DialogTitle>
              <DialogDescription className="text-sm text-[color:var(--text-2)]">
                Nifty Satvik is invite-only. Fill out this form and we'll be in touch.
              </DialogDescription>
            </DialogHeader>
            <form onSubmit={handleSubmit} className="space-y-4 mt-4">
              <div className="space-y-2">
                <label className="text-xs font-medium text-[color:var(--text-2)]">Name *</label>
                <input
                  placeholder="Your full name"
                  value={formData.name}
                  onChange={(e) => setFormData((p) => ({ ...p, name: e.target.value }))}
                  className="flex h-11 w-full rounded-md bg-white/[0.04] border border-white/[0.1] text-white placeholder:text-[color:var(--text-3)] px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[color:var(--brand)]/50"
                  required
                />
              </div>
              <div className="space-y-2">
                <label className="text-xs font-medium text-[color:var(--text-2)]">Email *</label>
                <input
                  type="email"
                  placeholder="you@example.com"
                  value={formData.email}
                  onChange={(e) => setFormData((p) => ({ ...p, email: e.target.value }))}
                  className="flex h-11 w-full rounded-md bg-white/[0.04] border border-white/[0.1] text-white placeholder:text-[color:var(--text-3)] px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[color:var(--brand)]/50"
                  required
                />
              </div>
              <div className="space-y-2">
                <label className="text-xs font-medium text-[color:var(--text-2)]">Trading experience</label>
                <input
                  placeholder="e.g., 3 years active trading"
                  value={formData.trading_experience}
                  onChange={(e) => setFormData((p) => ({ ...p, trading_experience: e.target.value }))}
                  className="flex h-11 w-full rounded-md bg-white/[0.04] border border-white/[0.1] text-white placeholder:text-[color:var(--text-3)] px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[color:var(--brand)]/50"
                />
              </div>
              <div className="space-y-2">
                <label className="text-xs font-medium text-[color:var(--text-2)]">Why do you want access?</label>
                <textarea
                  placeholder="Tell us about your trading style..."
                  value={formData.message}
                  onChange={(e) => setFormData((p) => ({ ...p, message: e.target.value }))}
                  rows={3}
                  className="w-full rounded-md bg-white/[0.04] border border-white/[0.1] text-white placeholder:text-[color:var(--text-3)] px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[color:var(--brand)]/50 resize-none"
                />
              </div>
              {error && <p className="text-xs text-[color:var(--bear)]">{error}</p>}
              <button
                type="submit"
                disabled={loading}
                className="w-full h-11 text-sm font-medium disabled:opacity-70 transition-colors duration-200 flex items-center justify-center gap-2"
                style={{
                  background: "var(--brand)",
                  color: "var(--brand-fg)",
                  borderRadius: "var(--r-chip)",
                  border: "none",
                  letterSpacing: "-0.005em",
                }}
              >
                {loading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Submitting...
                  </>
                ) : (
                  "Submit request"
                )}
              </button>
            </form>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}
