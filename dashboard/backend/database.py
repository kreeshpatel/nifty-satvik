"""
NiftyQuant Database — SQLAlchemy models and session management.
Uses PostgreSQL on Render via DATABASE_URL.
"""

import os
from datetime import datetime

from sqlalchemy import (
    create_engine, Column, Integer, String, Boolean, DateTime, Date, Float,
    ForeignKey, Text, UniqueConstraint, event
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

DATABASE_URL = os.getenv("DATABASE_URL", "")
# Render provides postgres:// but SQLAlchemy needs postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Enforce TLS to Postgres. Render's managed Postgres supports it but the
# default DSN doesn't include sslmode — without this, a misconfigured
# proxy or future migration could silently fall back to plaintext.
# For local dev against a non-SSL Postgres, set sslmode=disable explicitly
# in your DATABASE_URL.
if DATABASE_URL.startswith("postgresql://") and "sslmode=" not in DATABASE_URL:
    sep = "&" if "?" in DATABASE_URL else "?"
    DATABASE_URL = f"{DATABASE_URL}{sep}sslmode=require"

engine = create_engine(DATABASE_URL, pool_pre_ping=True) if DATABASE_URL else None
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False) if engine else None

Base = declarative_base()


# ── Models ────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(100), nullable=False)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime, nullable=True)
    last_active = Column(DateTime, nullable=True)
    mfa_enabled = Column(Boolean, default=False, nullable=False)
    mfa_secret_encrypted = Column(Text, nullable=True)
    # Signals-page position sizer preferences (added 2026-07-13). risk_tier keys
    # into config.RISK_TIERS ('medium'|'high'); default_capital remembers the last
    # capital the user sized against so the sizer isn't blank on return.
    risk_tier = Column(String(16), nullable=False, default="medium", server_default="medium")
    default_capital = Column(Float, nullable=True)

    kite_session = relationship("KiteSession", back_populates="user", uselist=False)
    refresh_tokens = relationship("RefreshToken", back_populates="user")
    audit_logs = relationship("AuditLog", back_populates="user")


class KiteSession(Base):
    __tablename__ = "kite_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    kite_user_id = Column(String(50), nullable=True)
    access_token_encrypted = Column(Text, nullable=False)
    expires_at = Column(Float, nullable=False)

    user = relationship("User", back_populates="kite_session")


class HdfcMarketDataSession(Base):
    """The shared HDFC Securities (InvestRight) access token used ONLY for market
    data (LTP) — never for orders/holdings/positions, which stay on Kite. There is
    exactly one row: HDFC's login flow needs a human to answer an OTP each time
    (no TOTP option confirmed), so this is completed by an admin via
    /api/admin/hdfc/login/*, not an unattended per-user OAuth flow like Kite.

    `connected_by_user_id` records who last completed the login (audit only).
    """
    __tablename__ = "hdfc_market_data_sessions"

    id = Column(Integer, primary_key=True, index=True)
    access_token_encrypted = Column(Text, nullable=False)
    obtained_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    # HDFC's token validity period isn't documented anywhere we could find —
    # nullable until we observe a real expiry (a 401 from /fetch-ltp) and can
    # start enforcing/tracking it.
    expires_at = Column(DateTime, nullable=True)
    connected_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)


class RefreshToken(Base):
    """
    Refresh-token chain with reuse detection.

    Each rotation links the new token to the old one via parent_token_hash.
    Old tokens are NOT deleted — they're marked with revoked_at so a replay
    of an already-rotated token is detectable as theft.

    On /auth/refresh:
      - Token hash matches an active row (revoked_at IS NULL) → rotate.
      - Token hash matches a revoked row → REUSE DETECTED → revoke the
        entire chain for that user_id (force re-login).
      - Token hash matches no row → 401 invalid/expired.

    parent_token_hash and revoked_at are nullable so create_all() can add
    them to an existing DB; the manual ALTER TABLE in init_db() handles
    the live migration when the Render service redeploys.
    """
    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash = Column(String(255), unique=True, nullable=False, index=True)
    parent_token_hash = Column(String(255), nullable=True, index=True)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    revoked_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="refresh_tokens")


class PasswordResetToken(Base):
    """
    Single-use password-reset token.

    On /auth/forgot-password we store sha256(raw_token) — the raw string is
    only ever in the email URL. On /auth/reset-password the row is consumed
    (used_at set) so a token cannot be replayed even within its 30-min TTL.
    """
    __tablename__ = "password_reset_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"),
                     nullable=False, index=True)
    token_hash = Column(String(255), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action = Column(String(50), nullable=False, index=True)
    detail = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    user = relationship("User", back_populates="audit_logs")


class AccessRequest(Base):
    __tablename__ = "access_requests"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(255), nullable=False, index=True)
    trading_experience = Column(String(255), nullable=True)
    message = Column(Text, nullable=True)
    status = Column(String(20), default="pending", index=True)  # pending, approved, rejected
    ip_address = Column(String(45), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    reviewed_at = Column(DateTime, nullable=True)
    reviewed_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)


class NQOrder(Base):
    """
    NiftyQuant-executed orders — only orders placed through our Buy/Sell
    buttons live here. External Kite trades (placed directly on kite.zerodha.com
    or another client) are intentionally NOT tracked, so that the Accounting
    and Journal pages show only trades that came from a NiftyQuant signal.

    Lifecycle:
      1. Frontend POSTs to /api/kite/orders/:variety (creates Kite order)
      2. Frontend POSTs to /api/nq-orders with { kite_order_id, signal_id, ... }
         → status = PENDING
      3. WS order_update from Kite → ws_manager patches this row:
         - OPEN      → still working
         - COMPLETE  → fill_price / filled_at / net_amount set
         - REJECTED  → terminal, with reason
         - CANCELLED → terminal (user cancelled from our UI or Kite web)

    Defaults are set on every nullable column so Base.metadata.create_all()
    adds the table to an existing Render DB without needing Alembic.
    """
    __tablename__ = "nq_orders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"),
                     nullable=False, index=True)

    # Kite broker order id, returned by kite.place_order. Unique because Kite
    # guarantees global uniqueness across all users within an account; we
    # index it for the WS patching hot-path lookup.
    kite_order_id = Column(String(64), unique=True, nullable=True, index=True)

    # Logical signal id — "{ticker}__{signal_date}". Lets us group all
    # orders (entry + trim + full exit) for the same trade idea on the
    # Journal + Accounting pages.
    signal_id = Column(String(128), nullable=True, index=True)

    ticker = Column(String(32), nullable=False, index=True)
    action = Column(String(8), nullable=False)                # BUY | SELL
    qty = Column(Integer, nullable=False, default=0)
    placed_price = Column(Float, nullable=True)               # LIMIT entry price
    fill_price = Column(Float, nullable=True)                 # avg fill from WS
    brokerage = Column(Float, nullable=True, default=0.0)
    stt = Column(Float, nullable=True, default=0.0)
    net_amount = Column(Float, nullable=True)

    status = Column(String(16), nullable=False, default="PENDING", index=True)
    # PENDING → placed locally, awaiting Kite ack
    # OPEN    → Kite accepted, order working
    # COMPLETE → fully filled
    # REJECTED → Kite rejected (insufficient funds, invalid price, etc.)
    # CANCELLED → user or system cancelled

    placed_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    filled_at = Column(DateTime, nullable=True)

    source = Column(String(32), nullable=False, default="niftyquant_signal")
    notes = Column(Text, nullable=True)                       # journal rationale

    user = relationship("User")


class NavHistory(Base):
    """
    Per-user daily NAV snapshot for the Equity Curve.

    Populated by the snapshot helper in services/nav_history.py whenever
    /api/positions/nq is hit (i.e. every dashboard load). Idempotent on
    (user_id, snapshot_date) — multiple visits same day update the same
    row with the latest intraday NAV rather than appending duplicates.

    No backfill exists — series starts on the day we shipped this and
    grows from there. Charts render gracefully on partial data; an
    explicit "less than 7 days of history" note is shown by the
    frontend when count < 7.

    Columns:
      nav             cash + holdings_market_value (Kite truth)
      cash            margins.available + margins.used (cash + blocked)
      holdings_value  sum(last_price * effective_qty) across Kite holdings
      day_pnl         today's P&L at snapshot time (uses fallback if Kite's
                      day_change field is 0 — same logic as the KPI tiles)
    """
    __tablename__ = "nav_history"
    __table_args__ = (
        UniqueConstraint("user_id", "snapshot_date", name="uix_nav_user_date"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"),
                     nullable=False, index=True)
    snapshot_date = Column(Date, nullable=False, index=True)
    nav = Column(Float, nullable=False)
    cash = Column(Float, nullable=False, default=0.0)
    holdings_value = Column(Float, nullable=False, default=0.0)
    day_pnl = Column(Float, nullable=False, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User")


class UserWatchlist(Base):
    """Per-user saved-stocks list (the left watchlist rail).

    Stores only membership — (user_id, ticker) — never prices. Quotes are
    fetched from the shared, centralized quote endpoints. A brand-new table,
    so Base.metadata.create_all() creates it on startup (no migration needed).
    """
    __tablename__ = "user_watchlists"
    __table_args__ = (
        # A ticker lives once per (user, list). list_no lets a user keep two
        # independent lists (1 = the seeded core list, 2 = a blank scratch list).
        UniqueConstraint("user_id", "list_no", "ticker", name="uix_watchlist_user_list_ticker"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"),
                     nullable=False, index=True)
    ticker = Column(String(32), nullable=False, index=True)
    # Which of the user's lists this row belongs to. 1 = core (seeded with a
    # few Nifty-50 names on first use), 2 = the user's own blank list.
    list_no = Column(Integer, nullable=False, default=1, server_default="1", index=True)
    sort_order = Column(Integer, nullable=False, default=0)
    added_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User")


class UserHolding(Base):
    """Per-user EPHEMERAL 'I bought this signal' marks (Signals page, added 2026-07-13).

    The user manually marks a research recommendation as bought; the row lives ONLY
    while the trade is open and is ERASED the moment the model completes the trade
    (target/stop/expiry — see routers/holdings.py, which prunes on read against the
    weekly history). There is NO lifecycle column and NO permanent per-user track
    record: the completed-trade record is the model's shared signals_history_weekly.json.

    Keyed by signal_id = '{ticker}__{signal_date}' — the same canonical key used by
    NQOrder.signal_id and nq_position_id — so a re-signal of the same name in a later
    week is a distinct record. NOT reused from NQOrder: that table is Kite-execution
    machinery (kite_order_id + WS fills) feeding the Accounting/Journal FY-P&L pages;
    a self-reported mark would pollute those. Brand-new table ⇒ create_all() handles it.
    """
    __tablename__ = "user_holdings"
    __table_args__ = (
        UniqueConstraint("user_id", "signal_id", name="uix_holding_user_signal"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"),
                     nullable=False, index=True)
    signal_id = Column(String(128), nullable=False, index=True)   # "{ticker}__{signal_date}"
    ticker = Column(String(32), nullable=False, index=True)
    entry = Column(Float, nullable=True)
    stop = Column(Float, nullable=True)
    qty = Column(Integer, nullable=True)                          # NULL = mark-only (no capital known)
    risk_tier_at_buy = Column(String(16), nullable=False, default="medium")
    bought_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User")


class ExecutionEvent(Base):
    """Per-user, append-only SELF-REPORTED execution ledger (Stage-4, docs/EXECUTION_CAPTURE_SPEC.md).

    With no broker connection (ADR 0011) the site only INSTRUCTS; the user executes on their own
    broker and reports each fill (qty + price) via a popup. Those reports land here as immutable
    EVENTS — one row per buy or partial sell — and this list IS the durable truth-of-record for a
    user's position, cost basis, and realized P&L. It supersedes the ephemeral, buy-only,
    erase-on-completion `UserHolding` mark:

    - APPEND-ONLY: a DB trigger (init_db, like signal_snapshots) blocks UPDATE/DELETE. A mistake is
      fixed by a NEW correcting event (`corrects_event_id` points at the row it supersedes), never an
      in-place edit — so the audit trail the dispute/integrity thread requires is preserved.
    - DURABLE: the position and its closed record survive model completion (no erase). A user's
      permanent per-user track record lives here, distinct from the model's shared paper history.
    - PARTIAL-AWARE: config P exits in three tranches (40%@2R / 40% pattern / 20% runner), so a SELL
      is rarely the whole position. Each event carries the qty + price for THAT fill; remaining qty and
      realized P&L are derived (quantity-weighted) in services/execution_ledger.py — never from the
      model's clean 2R/2.5R/SMA numbers.
    - Keyed by signal_id = '{ticker}__{signal_date}' (the canonical key) so a re-signal is a distinct
      position and a stale prior-episode hold is representable.
    - fill_source is always 'self_reported' — never presented as broker-verified. Kept OUT of the dead
      NQOrder/Kite tables so self-reports never mix with the retired broker-execution machinery.

    Created on startup by create_all(); the append-only trigger is added by init_db().
    """
    __tablename__ = "execution_events"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    signal_id = Column(String(128), nullable=False, index=True)   # "{ticker}__{signal_date}"
    ticker = Column(String(32), nullable=False, index=True)
    side = Column(String(4), nullable=False)                       # BUY | SELL
    qty = Column(Integer, nullable=False)                          # shares in THIS event (> 0)
    price = Column(Float, nullable=False)                          # self-reported execution price (> 0)
    tranche = Column(String(16), nullable=True)                    # sell tag: target|pattern|runner|manual
    fill_source = Column(String(24), nullable=False, default="self_reported")
    corrects_event_id = Column(Integer, nullable=True)             # this event supersedes that row (audit)
    note = Column(String(256), nullable=True)
    executed_at = Column(DateTime, nullable=True)                  # when the user says the fill happened
    risk_tier_at_buy = Column(String(16), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    user = relationship("User")


class SignalSnapshot(Base):
    """IMMUTABLE, hash-chained frozen snapshot of a signal as it was FIRST published.

    The research engine is idempotent — the cron recomputes the whole book from inception
    every Saturday (docs/PRODUCT_STATE_AND_DATA.md §2). But a card a user acted on is a
    CONTRACT: its entry band / stop / target / exit_plan must never change retroactively
    because the model recomputed off revised data. So the first time a signal_id is served,
    we freeze it here and never touch it again.

    - Append-only: a DB trigger (init_db, like audit_logs) blocks UPDATE/DELETE.
    - Hash-chained: content_hash = sha256(canonical fields + prev_hash) links each row to
      the prior one, so the whole chain is tamper-evident (dispute defensibility + leak
      provenance). model-GLOBAL (not per-user); the shared frozen record of what was shown.
    - Keyed by signal_id = "{ticker}__{signal_date}" — the canonical key shared with
      UserHolding / NQOrder, so a re-signal in a later week is a distinct frozen row.

    Created on startup by Base.metadata.create_all(); the trigger is added by init_db().
    """
    __tablename__ = "signal_snapshots"
    id = Column(Integer, primary_key=True, index=True)
    signal_id = Column(String(80), unique=True, nullable=False, index=True)
    ticker = Column(String(32), nullable=False)
    signal_date = Column(String(16), nullable=False)
    entry = Column(Float, nullable=False)
    stop = Column(Float, nullable=False)
    target = Column(Float, nullable=True)
    entry_low = Column(Float, nullable=True)
    entry_high = Column(Float, nullable=True)
    exit_plan_json = Column(Text, nullable=True)          # the frozen exit_plan, JSON-serialised
    actionability = Column(String(32), nullable=True)
    generated_at = Column(String(32), nullable=True)      # the envelope's as-of when first frozen
    status = Column(String(16), nullable=False, default="OK")   # OK | QUARANTINED (integrity gate)
    content_hash = Column(String(64), nullable=False)
    prev_hash = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


# ── DB Session Dependency ─────────────────────────────

def get_db():
    """FastAPI dependency that yields a DB session."""
    if SessionLocal is None:
        raise RuntimeError("DATABASE_URL not configured")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables (called on startup)."""
    if engine is None:
        return

    Base.metadata.create_all(bind=engine)

    # Idempotent live migrations for tables that already exist on Render.
    #
    # Each step runs in its own short-lived transaction with a 3s lock_timeout
    # and a try/except wrapper. Rationale: during a Render rolling deploy the
    # OLD container is still serving requests and holding read locks on these
    # tables, so a naive ALTER TABLE / CREATE TRIGGER blocks waiting for an
    # ACCESS EXCLUSIVE lock — startup hangs, the new container never binds
    # its port, and Render kills it. Failing fast + skipping is safe because
    # every step is a no-op on subsequent runs (IF NOT EXISTS / CREATE OR
    # REPLACE) — once the old container exits and lock contention clears,
    # the next restart picks them up cleanly.
    import logging as _logging
    from sqlalchemy import text
    from sqlalchemy.exc import OperationalError, ProgrammingError

    _migration_logger = _logging.getLogger("niftyquant.db_migration")

    def _run_migration(label: str, sql: str) -> None:
        try:
            with engine.begin() as conn:
                conn.execute(text("SET LOCAL lock_timeout = '3s'"))
                conn.execute(text(sql))
            _migration_logger.info("migration ok: %s", label)
        except (OperationalError, ProgrammingError) as e:
            # OperationalError covers lock_timeout / canceling-statement-due-to-statement-timeout.
            # ProgrammingError catches things like "permission denied for function ..."
            # (Render free-tier role can't always CREATE FUNCTION). Both are
            # non-fatal — the next clean restart will retry idempotently.
            _migration_logger.warning(
                "migration deferred (%s): %s — will retry on next restart",
                label, str(e).splitlines()[0] if str(e) else type(e).__name__,
            )

    # P0-5: refresh-token reuse detection columns
    _run_migration("refresh_tokens.parent_token_hash",
        "ALTER TABLE refresh_tokens ADD COLUMN IF NOT EXISTS parent_token_hash VARCHAR(255)")
    _run_migration("refresh_tokens.revoked_at",
        "ALTER TABLE refresh_tokens ADD COLUMN IF NOT EXISTS revoked_at TIMESTAMP")
    _run_migration("ix_refresh_tokens_parent_token_hash",
        "CREATE INDEX IF NOT EXISTS ix_refresh_tokens_parent_token_hash "
        "ON refresh_tokens (parent_token_hash)")

    # P1-7: opt-in TOTP MFA columns on users
    _run_migration("users.mfa_enabled",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS mfa_enabled BOOLEAN NOT NULL DEFAULT FALSE")
    _run_migration("users.mfa_secret_encrypted",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS mfa_secret_encrypted TEXT")

    # Two-list watchlist: add list_no (existing rows backfill to list 1) and
    # swap the (user_id, ticker) unique constraint for (user_id, list_no,
    # ticker) so the same ticker can live in both lists. The DROP+ADD run in a
    # single transaction (one _run_migration call) so there's never a window
    # with no unique constraint. Both steps are idempotent.
    _run_migration("user_watchlists.list_no",
        "ALTER TABLE user_watchlists ADD COLUMN IF NOT EXISTS list_no INTEGER NOT NULL DEFAULT 1")
    _run_migration("user_watchlists.list_no_index",
        "CREATE INDEX IF NOT EXISTS ix_user_watchlists_list_no ON user_watchlists (list_no)")
    _run_migration("user_watchlists.unique_constraint_swap", """
        DO $$
        BEGIN
          ALTER TABLE user_watchlists DROP CONSTRAINT IF EXISTS uix_watchlist_user_ticker;
          IF NOT EXISTS (
            SELECT 1 FROM pg_constraint WHERE conname = 'uix_watchlist_user_list_ticker'
          ) THEN
            ALTER TABLE user_watchlists
              ADD CONSTRAINT uix_watchlist_user_list_ticker UNIQUE (user_id, list_no, ticker);
          END IF;
        END $$;
    """)

    # Signals sizer prefs on users (2026-07-13). New table user_holdings needs
    # no entry here — create_all() above adds it. These two columns land on the
    # existing users table, so they get idempotent ALTERs like the MFA block.
    _run_migration("users.risk_tier",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS risk_tier VARCHAR(16) NOT NULL DEFAULT 'medium'")
    _run_migration("users.default_capital",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS default_capital DOUBLE PRECISION")

    # P2-1: audit_logs append-only + 365-day retention enforcement.
    # The CREATE TRIGGER step needs ACCESS EXCLUSIVE on audit_logs, which
    # is the most likely thing to lose to lock contention during a rolling
    # deploy — that's exactly why each step is independently retriable.
    _run_migration("audit_logs_protect_function", """
        CREATE OR REPLACE FUNCTION audit_logs_protect()
        RETURNS TRIGGER AS $$
        BEGIN
            IF TG_OP = 'UPDATE' THEN
                RAISE EXCEPTION 'audit_logs is append-only';
            ELSIF TG_OP = 'DELETE' THEN
                IF OLD.timestamp < NOW() - INTERVAL '365 days' THEN
                    RETURN OLD;
                ELSE
                    RAISE EXCEPTION 'audit_logs entries cannot be deleted within the 365-day retention window';
                END IF;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
    """)
    _run_migration("audit_logs_protect_trigger_drop",
        "DROP TRIGGER IF EXISTS audit_logs_protect_trigger ON audit_logs")
    _run_migration("audit_logs_protect_trigger_create", """
        CREATE TRIGGER audit_logs_protect_trigger
        BEFORE UPDATE OR DELETE ON audit_logs
        FOR EACH ROW EXECUTE FUNCTION audit_logs_protect()
    """)

    # P2-3: opportunistic 365-day retention purge. Render restarts at least
    # once a day so this gives natural cadence without a separate cron.
    _run_migration("audit_logs_retention_purge",
        "DELETE FROM audit_logs WHERE timestamp < NOW() - INTERVAL '365 days'")

    # Stage-2: signal_snapshots is FULLY immutable (append-only, no updates, no deletes) —
    # a card a user acted on is a contract that must never change on a model recompute.
    # Same trigger pattern as audit_logs, but stricter (no retention-window delete).
    _run_migration("signal_snapshots_protect_function", """
        CREATE OR REPLACE FUNCTION signal_snapshots_protect()
        RETURNS TRIGGER AS $$
        BEGIN
            RAISE EXCEPTION 'signal_snapshots is immutable (append-only): % blocked', TG_OP;
        END;
        $$ LANGUAGE plpgsql
    """)
    _run_migration("signal_snapshots_protect_trigger_drop",
        "DROP TRIGGER IF EXISTS signal_snapshots_protect_trigger ON signal_snapshots")
    _run_migration("signal_snapshots_protect_trigger_create", """
        CREATE TRIGGER signal_snapshots_protect_trigger
        BEFORE UPDATE OR DELETE ON signal_snapshots
        FOR EACH ROW EXECUTE FUNCTION signal_snapshots_protect()
    """)

    # Stage-4: execution_events is the durable, APPEND-ONLY self-reported ledger (ADR 0011). A user's
    # position/cost-basis/realized-P&L is derived from these rows, so they must never be edited or
    # deleted in place — a correction is a NEW event (corrects_event_id). Same immutable trigger as
    # signal_snapshots; blocks UPDATE/DELETE so the audit trail is tamper-evident for disputes.
    _run_migration("execution_events_protect_function", """
        CREATE OR REPLACE FUNCTION execution_events_protect()
        RETURNS TRIGGER AS $$
        BEGIN
            RAISE EXCEPTION 'execution_events is append-only (self-reported ledger): % blocked', TG_OP;
        END;
        $$ LANGUAGE plpgsql
    """)
    _run_migration("execution_events_protect_trigger_drop",
        "DROP TRIGGER IF EXISTS execution_events_protect_trigger ON execution_events")
    _run_migration("execution_events_protect_trigger_create", """
        CREATE TRIGGER execution_events_protect_trigger
        BEFORE UPDATE OR DELETE ON execution_events
        FOR EACH ROW EXECUTE FUNCTION execution_events_protect()
    """)
