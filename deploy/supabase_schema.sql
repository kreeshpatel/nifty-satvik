-- NiftyQuant backend schema for Supabase Postgres (Render -> Supabase migration).
--
-- GENERATED from the SQLAlchemy models in dashboard/backend/database.py — matches
-- what the app's Base.metadata.create_all() produces on first boot, so applying this
-- here just makes the FastAPI startup a no-op. Idempotent (IF NOT EXISTS): safe to
-- re-run and safe to apply before/after the first API boot.
--
-- Apply via: Supabase Dashboard -> SQL Editor (paste + run), or the Supabase MCP
-- (execute_sql) after a Claude restart loads the server.
--
-- RLS is ENABLED on every table as defense-in-depth: the FastAPI app connects as the
-- `postgres` role (BYPASSRLS) via DATABASE_URL, so the app is unaffected, but the
-- Supabase Data API (PostgREST/anon) can never read these auth tables. No policies are
-- needed because nothing should reach these tables except the backend's direct connection.
--
-- NOTE: the app's init_db() additionally installs the audit_logs append-only trigger +
-- 365-day retention function on first boot — not repeated here (it needs the running app).

CREATE TABLE IF NOT EXISTS users (
	id SERIAL NOT NULL, 
	email VARCHAR(255) NOT NULL, 
	password_hash VARCHAR(255) NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	is_active BOOLEAN, 
	is_admin BOOLEAN, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	failed_login_attempts INTEGER, 
	locked_until TIMESTAMP WITHOUT TIME ZONE, 
	last_active TIMESTAMP WITHOUT TIME ZONE, 
	mfa_enabled BOOLEAN NOT NULL, 
	mfa_secret_encrypted TEXT, 
	PRIMARY KEY (id)
);
CREATE INDEX IF NOT EXISTS ix_users_id ON users (id);
CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email ON users (email);
CREATE TABLE IF NOT EXISTS access_requests (
	id SERIAL NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	email VARCHAR(255) NOT NULL, 
	trading_experience VARCHAR(255), 
	message TEXT, 
	status VARCHAR(20), 
	ip_address VARCHAR(45), 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	reviewed_at TIMESTAMP WITHOUT TIME ZONE, 
	reviewed_by INTEGER, 
	PRIMARY KEY (id), 
	FOREIGN KEY(reviewed_by) REFERENCES users (id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS ix_access_requests_email ON access_requests (email);
CREATE INDEX IF NOT EXISTS ix_access_requests_id ON access_requests (id);
CREATE INDEX IF NOT EXISTS ix_access_requests_created_at ON access_requests (created_at);
CREATE INDEX IF NOT EXISTS ix_access_requests_status ON access_requests (status);
CREATE TABLE IF NOT EXISTS audit_logs (
	id SERIAL NOT NULL, 
	user_id INTEGER, 
	action VARCHAR(50) NOT NULL, 
	detail TEXT, 
	ip_address VARCHAR(45), 
	timestamp TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS ix_audit_logs_timestamp ON audit_logs (timestamp);
CREATE INDEX IF NOT EXISTS ix_audit_logs_action ON audit_logs (action);
CREATE INDEX IF NOT EXISTS ix_audit_logs_id ON audit_logs (id);
CREATE TABLE IF NOT EXISTS kite_sessions (
	id SERIAL NOT NULL, 
	user_id INTEGER NOT NULL, 
	kite_user_id VARCHAR(50), 
	access_token_encrypted TEXT NOT NULL, 
	expires_at FLOAT NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (user_id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS ix_kite_sessions_id ON kite_sessions (id);
CREATE TABLE IF NOT EXISTS nav_history (
	id SERIAL NOT NULL, 
	user_id INTEGER NOT NULL, 
	snapshot_date DATE NOT NULL, 
	nav FLOAT NOT NULL, 
	cash FLOAT NOT NULL, 
	holdings_value FLOAT NOT NULL, 
	day_pnl FLOAT NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uix_nav_user_date UNIQUE (user_id, snapshot_date), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS ix_nav_history_id ON nav_history (id);
CREATE INDEX IF NOT EXISTS ix_nav_history_user_id ON nav_history (user_id);
CREATE INDEX IF NOT EXISTS ix_nav_history_snapshot_date ON nav_history (snapshot_date);
CREATE TABLE IF NOT EXISTS nq_orders (
	id SERIAL NOT NULL, 
	user_id INTEGER NOT NULL, 
	kite_order_id VARCHAR(64), 
	signal_id VARCHAR(128), 
	ticker VARCHAR(32) NOT NULL, 
	action VARCHAR(8) NOT NULL, 
	qty INTEGER NOT NULL, 
	placed_price FLOAT, 
	fill_price FLOAT, 
	brokerage FLOAT, 
	stt FLOAT, 
	net_amount FLOAT, 
	status VARCHAR(16) NOT NULL, 
	placed_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	filled_at TIMESTAMP WITHOUT TIME ZONE, 
	source VARCHAR(32) NOT NULL, 
	notes TEXT, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);
CREATE UNIQUE INDEX IF NOT EXISTS ix_nq_orders_kite_order_id ON nq_orders (kite_order_id);
CREATE INDEX IF NOT EXISTS ix_nq_orders_status ON nq_orders (status);
CREATE INDEX IF NOT EXISTS ix_nq_orders_id ON nq_orders (id);
CREATE INDEX IF NOT EXISTS ix_nq_orders_ticker ON nq_orders (ticker);
CREATE INDEX IF NOT EXISTS ix_nq_orders_user_id ON nq_orders (user_id);
CREATE INDEX IF NOT EXISTS ix_nq_orders_placed_at ON nq_orders (placed_at);
CREATE INDEX IF NOT EXISTS ix_nq_orders_signal_id ON nq_orders (signal_id);
CREATE TABLE IF NOT EXISTS password_reset_tokens (
	id SERIAL NOT NULL, 
	user_id INTEGER NOT NULL, 
	token_hash VARCHAR(255) NOT NULL, 
	expires_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	used_at TIMESTAMP WITHOUT TIME ZONE, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS ix_password_reset_tokens_id ON password_reset_tokens (id);
CREATE INDEX IF NOT EXISTS ix_password_reset_tokens_user_id ON password_reset_tokens (user_id);
CREATE UNIQUE INDEX IF NOT EXISTS ix_password_reset_tokens_token_hash ON password_reset_tokens (token_hash);
CREATE TABLE IF NOT EXISTS refresh_tokens (
	id SERIAL NOT NULL, 
	user_id INTEGER NOT NULL, 
	token_hash VARCHAR(255) NOT NULL, 
	parent_token_hash VARCHAR(255), 
	expires_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	revoked_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS ix_refresh_tokens_parent_token_hash ON refresh_tokens (parent_token_hash);
CREATE INDEX IF NOT EXISTS ix_refresh_tokens_id ON refresh_tokens (id);
CREATE UNIQUE INDEX IF NOT EXISTS ix_refresh_tokens_token_hash ON refresh_tokens (token_hash);

-- Defense-in-depth: lock every table to the backend's direct connection only.
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.access_requests ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.kite_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.nav_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.nq_orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.password_reset_tokens ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.refresh_tokens ENABLE ROW LEVEL SECURITY;
