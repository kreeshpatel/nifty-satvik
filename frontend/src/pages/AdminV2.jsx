/**
 * AdminV2 — Phase A redesign of the admin operations console.
 *
 * Hero: sticky 4-stat strip — cron · owner Kite · users · pending access requests.
 *
 * Tabs (chosen by user 2026-04-27):
 *   1. Users           — DataTable + side drawer with action buttons
 *   2. Access Requests — card grid + approve / reject / delete
 *   3. System          — health KPI + audit log feed
 *   4. Operations      — manual scan + Kite refresh + future ops
 *
 * Page is gated to `user.is_admin` at the App.js layer; if a non-admin
 * lands here they get redirected via the existing AdminRoute guard.
 */
import React, { useContext, useMemo, useState } from 'react';
import { Navigate } from 'react-router-dom';
import {
  Activity, AlertCircle, Check, Clock, Database, Inbox, KeyRound,
  PlayCircle, Plug, RefreshCcw, Search, Shield, Trash2, UserPlus, X, Zap,
} from 'lucide-react';
import { toast } from 'sonner';
import { PageShell } from '@/components/shared/PageShell';
import { KPICard } from '@/components/shared/KPICard';
import { DataTable } from '@/components/shared/DataTable';
import { StatusChip } from '@/components/shared/StatusChip';
import { EmptyState } from '@/components/shared/EmptyState';
import {
  useAdminUsers, useAdminAuditLogs, useAdminKiteStatus, useAdminSystemHealth,
  useAdminAccessRequests, useAdminUserMutation, useAdminCreateUserMutation,
  useAdminRefreshKiteMutation, useAdminRunScanMutation, useAdminAccessRequestMutations,
} from '@/hooks/queries/useAdmin';
import { useSignals } from '@/hooks/queries/useSignals';
import { AuthContext } from '@/context/AuthContext';
import { fmtRelTime } from '@/lib/format';

const TABS = [
  { value: 'users',     label: 'Users',           icon: Shield },
  { value: 'access',    label: 'Access Requests', icon: Inbox },
  { value: 'system',    label: 'System',          icon: Activity },
  { value: 'operations', label: 'Operations',     icon: PlayCircle },
];

export default function AdminV2() {
  const { user } = useContext(AuthContext);
  const [tab, setTab] = useState('users');

  // Primary path: GET /api/admin/system-health returns everything in one call.
  // Fallback path: when that endpoint isn't deployed yet (Render lags Vercel)
  // OR errors out, we compose the same shape from the per-endpoint queries
  // that have always been available — kite-status + users + access-requests
  // + signals. That way the hero strip is correct even before the new
  // backend ships.
  const healthQuery = useAdminSystemHealth();
  const fallbackKite = useAdminKiteStatus({
    enabled: !healthQuery.isLoading && (!!healthQuery.error || !healthQuery.data),
  });
  const fallbackUsers = useAdminUsers({
    enabled: !healthQuery.isLoading && (!!healthQuery.error || !healthQuery.data),
  });
  const fallbackAccess = useAdminAccessRequests('pending', {
    enabled: !healthQuery.isLoading && (!!healthQuery.error || !healthQuery.data),
  });
  const fallbackSignals = useSignals({
    enabled: !healthQuery.isLoading && (!!healthQuery.error || !healthQuery.data),
  });

  const health = useMemo(() => {
    if (healthQuery.data) return healthQuery.data;
    // Compose fallback shape matching /api/admin/system-health response.
    const usersList = fallbackUsers.data ?? [];
    const kiteOwner = fallbackKite.data ?? {};
    const pendingAccess = (fallbackAccess.data ?? []).filter(
      (r) => String(r.status || '').toLowerCase() === 'pending',
    ).length;
    const signalsBlob = fallbackSignals.data ?? {};
    const cronHealth = signalsBlob?.cron_health ?? {};
    return {
      cron: {
        status:    cronHealth.status ?? 'UNKNOWN',
        scan_time: signalsBlob?.scan_time,
        n_signals: signalsBlob?.n_signals,
      },
      kite_owner: kiteOwner,
      users: {
        total:          usersList.length,
        active:         usersList.filter((u) => u.is_active && !isLocked(u)).length,
        locked:         usersList.filter(isLocked).length,
        suspended:      usersList.filter((u) => !u.is_active).length,
        kite_connected: usersList.filter((u) => u.kite_connected).length,
      },
      access: { pending: pendingAccess },
      errors_24h: 0,
    };
  }, [
    healthQuery.data,
    fallbackKite.data,
    fallbackUsers.data,
    fallbackAccess.data,
    fallbackSignals.data,
  ]);

  // Hard-gate: non-admins shouldn't see this page even if they hit /admin directly.
  if (user && !user.is_admin) return <Navigate to="/dashboard" replace />;

  return (
    <PageShell title="Admin" heroTone="warn">
      <header style={{ paddingTop: 24, paddingBottom: 16 }}>
        <h1 className="t-title-1" style={{ margin: 0, color: 'var(--text-1)' }}>Admin</h1>
        <p className="t-ui-body" style={{ color: 'var(--text-2)', margin: '8px 0 0' }}>
          User management · system health · manual operations.
        </p>
      </header>

      {/* HERO STAT STRIP */}
      <HeroStrip
        health={health}
        loading={healthQuery.isLoading && !healthQuery.data && !fallbackUsers.data}
      />

      {/* TAB STRIP */}
      <TabStrip tabs={TABS} active={tab} onChange={setTab} />

      {tab === 'users'      && <UsersTab />}
      {tab === 'access'     && <AccessRequestsTab />}
      {tab === 'system'     && <SystemTab health={health} />}
      {tab === 'operations' && <OperationsTab />}
    </PageShell>
  );
}

// ══════════════════════════════════════════════════════════════
// HERO STRIP — sticky 4-stat overview
// ══════════════════════════════════════════════════════════════

function HeroStrip({ health, loading }) {
  if (loading) {
    return (
      <section
        className="grid"
        style={{
          gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
          gap: 16,
          marginBottom: 24,
        }}
      >
        {[0, 1, 2, 3].map((i) => (
          <div
            key={i}
            style={{
              background: 'var(--surface-1)',
              border: '1px solid var(--edge-1)',
              borderRadius: 'var(--r-card)',
              minHeight: 100,
              animation: 'skelPulse 1.8s ease-in-out infinite',
            }}
          />
        ))}
        <style>{`@keyframes skelPulse { 0%, 100% { opacity: 1 } 50% { opacity: 0.6 } }`}</style>
      </section>
    );
  }

  const cron = health?.cron ?? {};
  const kite = health?.kite_owner ?? {};
  const users = health?.users ?? {};
  const access = health?.access ?? {};
  const errors24h = health?.errors_24h ?? 0;

  const cronTone =
    cron.status === 'OK' ? 'bull'
    : cron.status === 'STALE' ? 'warn'
    : cron.status === 'FAILED_TODAY' ? 'bear'
    : 'muted';

  const kiteTone = kite.connected ? 'bull' : 'bear';

  return (
    <section
      className="grid"
      style={{
        gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
        gap: 16,
        marginBottom: 24,
      }}
    >
      <KPICard
        label="CRON"
        value={cron.status || 'UNKNOWN'}
        tone={cronTone}
        context={
          cron.scan_time
            ? `Scan ${fmtRelTime(new Date(cron.scan_time))} · ${cron.n_signals ?? 0} signals`
            : 'Never run'
        }
      />
      <KPICard
        label="OWNER KITE"
        value={kite.connected ? 'CONNECTED' : 'DISCONNECTED'}
        tone={kiteTone}
        context={
          kite.kite_user_id
            ? `${kite.kite_user_id}${kite.expires_at_iso ? ` · ${formatExpiry(kite.expires_at_iso)}` : ''}`
            : 'No owner session'
        }
      />
      <KPICard
        label="USERS"
        value={String(users.total ?? 0)}
        tone="neutral"
        context={
          `${users.active ?? 0} active · ${users.kite_connected ?? 0} on Kite${users.locked ? ` · ${users.locked} locked` : ''}`
        }
      />
      <KPICard
        label="PENDING REQUESTS"
        value={String(access.pending ?? 0)}
        tone={access.pending > 0 ? 'warn' : 'neutral'}
        context={errors24h > 0 ? `${errors24h} backend errors in 24h` : 'No backend errors in 24h'}
      />
    </section>
  );
}

function formatExpiry(iso) {
  try {
    const d = new Date(iso);
    return `expires ${d.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })}`;
  } catch {
    return 'expiry unknown';
  }
}

// ══════════════════════════════════════════════════════════════
// USERS TAB
// ══════════════════════════════════════════════════════════════

function UsersTab() {
  const usersQuery = useAdminUsers();
  const userMut = useAdminUserMutation();
  const createMut = useAdminCreateUserMutation();

  const [search, setSearch] = useState('');
  const [filter, setFilter] = useState('ALL');   // ALL | ACTIVE | LOCKED | SUSPENDED | KITE_OFF
  const [selected, setSelected] = useState(null);
  const [showCreate, setShowCreate] = useState(false);

  // Stable ref for downstream useMemo dep — see SignalsV2 for the same pattern.
  const users = useMemo(() => usersQuery.data ?? [], [usersQuery.data]);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return users.filter((u) => {
      if (q) {
        const haystack = `${u.name ?? ''} ${u.email ?? ''}`.toLowerCase();
        if (!haystack.includes(q)) return false;
      }
      if (filter === 'ACTIVE')    return u.is_active && !isLocked(u);
      if (filter === 'LOCKED')    return isLocked(u);
      if (filter === 'SUSPENDED') return !u.is_active;
      if (filter === 'KITE_OFF')  return !u.kite_connected;
      return true;
    });
  }, [users, search, filter]);

  const handleAction = async (userId, action, label) => {
    try {
      await userMut.mutateAsync({ userId, action });
      toast.success(label);
    } catch (e) {
      toast.error(`Action failed: ${e?.message ?? 'unknown error'}`);
    }
  };

  return (
    <div style={{ marginTop: 16 }}>
      {/* SEARCH + FILTER PILLS */}
      <div className="flex items-center" style={{ gap: 12, marginBottom: 16, flexWrap: 'wrap' }}>
        <div
          className="flex items-center"
          style={{
            flex: 1,
            minWidth: 240,
            background: 'var(--surface-1)',
            border: '1px solid var(--edge-1)',
            borderRadius: 'var(--r-chip)',
            padding: '0 12px',
            gap: 8,
          }}
        >
          <Search size={14} strokeWidth={1.75} style={{ color: 'var(--text-3)' }} />
          <input
            type="text"
            placeholder="Search by name or email…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="t-ui-body"
            style={{
              flex: 1,
              background: 'transparent',
              border: 'none',
              padding: '10px 0',
              color: 'var(--text-1)',
              outline: 'none',
              fontFamily: 'var(--font-sans)',
            }}
          />
        </div>
        <div className="flex items-center" style={{ gap: 6 }}>
          {[
            { v: 'ALL',       label: 'All' },
            { v: 'ACTIVE',    label: 'Active' },
            { v: 'LOCKED',    label: 'Locked' },
            { v: 'SUSPENDED', label: 'Suspended' },
            { v: 'KITE_OFF',  label: 'No Kite' },
          ].map((p) => {
            const active = filter === p.v;
            return (
              <button
                key={p.v}
                type="button"
                onClick={() => setFilter(p.v)}
                aria-pressed={active}
                className="t-ui-callout"
                style={{
                  padding: '8px 12px',
                  background: active ? 'var(--brand-soft)' : 'transparent',
                  color: active ? 'var(--brand-hi)' : 'var(--text-2)',
                  border: `1px solid ${active ? 'var(--brand-edge)' : 'var(--edge-1)'}`,
                  borderRadius: 'var(--r-chip)',
                  cursor: 'pointer',
                  fontWeight: active ? 600 : 500,
                }}
              >
                {p.label}
              </button>
            );
          })}
        </div>
        <button
          type="button"
          onClick={() => setShowCreate(true)}
          className="t-ui-callout"
          style={{
            padding: '8px 14px',
            background: 'var(--brand)',
            color: 'var(--brand-fg)',
            border: '1px solid var(--brand)',
            borderRadius: 'var(--r-chip)',
            cursor: 'pointer',
            fontWeight: 600,
            display: 'inline-flex',
            alignItems: 'center',
            gap: 6,
            whiteSpace: 'nowrap',
          }}
        >
          <UserPlus size={14} strokeWidth={1.75} />
          New user
        </button>
      </div>

      {usersQuery.isLoading ? (
        <TableSkeleton rows={6} cols={6} />
      ) : usersQuery.error ? (
        <ShellCard>
          <EmptyState icon={<AlertCircle />} title="Couldn't load users" body={String(usersQuery.error?.message ?? '')} />
        </ShellCard>
      ) : filtered.length === 0 ? (
        <ShellCard>
          <EmptyState icon={<Search />} title="No users match" body="Adjust the filter or search to see other rows." />
        </ShellCard>
      ) : (
        <DataTable
          rows={filtered.map((u, i) => ({ id: u.id ?? i, ...u }))}
          onRowClick={(u) => setSelected(u)}
          initialSort={{ key: 'last_active', dir: 'desc' }}
          columns={[
            { key: 'name', header: 'Name', sortable: true, width: '180px' },
            { key: 'email', header: 'Email', sortable: true },
            {
              key: 'role',
              header: 'Role',
              width: '100px',
              render: (_, u) => (
                u.is_admin
                  ? <StatusChip tone="brand">ADMIN</StatusChip>
                  : <StatusChip tone="muted">MEMBER</StatusChip>
              ),
            },
            {
              key: 'state',
              header: 'State',
              width: '120px',
              render: (_, u) => {
                if (!u.is_active) return <StatusChip tone="bear">SUSPENDED</StatusChip>;
                if (isLocked(u)) return <StatusChip tone="warn">LOCKED</StatusChip>;
                return <StatusChip tone="bull">ACTIVE</StatusChip>;
              },
            },
            {
              key: 'kite_connected',
              header: 'Kite',
              width: '90px',
              render: (v) =>
                v ? <StatusChip tone="bull">ON</StatusChip> : <StatusChip tone="muted">OFF</StatusChip>,
            },
            {
              key: 'last_active',
              header: 'Last seen',
              sortable: true,
              align: 'right',
              render: (v) => (v ? fmtRelTime(new Date(v)) : '—'),
            },
          ]}
        />
      )}

      <UserDetailDrawer
        user={selected}
        open={!!selected}
        onOpenChange={(open) => !open && setSelected(null)}
        onAction={handleAction}
        pending={userMut.isPending}
      />

      <CreateUserPanel
        open={showCreate}
        onOpenChange={setShowCreate}
        onCreate={async (form) => {
          try {
            const res = await createMut.mutateAsync(form);
            toast.success(`User ${res?.email ?? form.email} created`);
            setShowCreate(false);
            return true;
          } catch (e) {
            // Backend returns a human-readable detail on 400 (weak password) /
            // 409 (email exists) — surface it verbatim so the admin can fix it.
            toast.error(e?.message ?? 'Failed to create user');
            return false;
          }
        }}
        pending={createMut.isPending}
      />
    </div>
  );
}

function CreateUserPanel({ open, onOpenChange, onCreate, pending }) {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  // Reset fields whenever the panel is opened so a prior aborted attempt
  // doesn't leak into the next one.
  React.useEffect(() => {
    if (open) { setName(''); setEmail(''); setPassword(''); }
  }, [open]);

  if (!open) return null;

  const canSubmit = name.trim().length >= 2 && email.trim() && password.length >= 12 && !pending;

  const submit = async (e) => {
    e.preventDefault();
    if (!canSubmit) return;
    const ok = await onCreate({
      name: name.trim(),
      email: email.trim().toLowerCase(),
      password,
    });
    if (ok) { setName(''); setEmail(''); setPassword(''); }
  };

  const inputStyle = {
    width: '100%',
    background: 'var(--surface-2)',
    border: '1px solid var(--edge-1)',
    borderRadius: 'var(--r-chip)',
    padding: '10px 12px',
    color: 'var(--text-1)',
    outline: 'none',
    fontFamily: 'var(--font-sans)',
  };
  const labelStyle = { color: 'var(--text-3)', display: 'block', marginBottom: 6 };

  return (
    <SidePanel open={open} onOpenChange={onOpenChange} title="Create user">
      <form onSubmit={submit} style={{ padding: '20px 24px', display: 'flex', flexDirection: 'column', gap: 16 }}>
        <div>
          <label className="t-ui-footnote" style={labelStyle} htmlFor="cu-name">Name</label>
          <input
            id="cu-name" type="text" value={name} required
            onChange={(e) => setName(e.target.value)}
            placeholder="Full name" className="t-ui-body" style={inputStyle}
          />
        </div>
        <div>
          <label className="t-ui-footnote" style={labelStyle} htmlFor="cu-email">Email</label>
          <input
            id="cu-email" type="email" value={email} required
            onChange={(e) => setEmail(e.target.value)}
            placeholder="user@example.com" className="t-ui-body" style={inputStyle}
          />
        </div>
        <div>
          <label className="t-ui-footnote" style={labelStyle} htmlFor="cu-password">Password</label>
          <input
            id="cu-password" type="text" value={password} required
            onChange={(e) => setPassword(e.target.value)}
            placeholder="At least 12 characters" className="t-ui-body"
            style={{ ...inputStyle, fontFamily: 'var(--font-mono)' }}
            autoComplete="off"
          />
          <p className="t-ui-footnote" style={{ color: 'var(--text-4)', margin: '8px 0 0' }}>
            Min 12 characters and at least 3 of: lowercase, uppercase, digit, symbol.
            Shown in plain text — copy it and share with the user securely.
            They can change it later via the login page's “Forgot password” link.
          </p>
        </div>

        <button
          type="submit"
          disabled={!canSubmit}
          className="t-ui-callout"
          style={{
            marginTop: 4,
            padding: '11px 18px',
            background: canSubmit ? 'var(--brand)' : 'var(--surface-3)',
            color: canSubmit ? 'var(--brand-fg)' : 'var(--text-3)',
            border: `1px solid ${canSubmit ? 'var(--brand)' : 'var(--edge-1)'}`,
            borderRadius: 'var(--r-chip)',
            cursor: canSubmit ? 'pointer' : 'not-allowed',
            fontWeight: 600,
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 8,
          }}
        >
          {pending
            ? <RefreshCcw size={14} strokeWidth={2} className="animate-spin" />
            : <UserPlus size={14} strokeWidth={1.75} />}
          {pending ? 'Creating…' : 'Create user'}
        </button>
      </form>
    </SidePanel>
  );
}

function isLocked(u) {
  if (!u?.locked_until) return false;
  const t = new Date(u.locked_until).getTime();
  return Number.isFinite(t) && t > Date.now();
}

function UserDetailDrawer({ user, open, onOpenChange, onAction, pending }) {
  if (!user) return null;
  const locked = isLocked(user);
  return (
    <SidePanel open={open} onOpenChange={onOpenChange} title={user.name || 'User'}>
      <div style={{ padding: '20px 24px' }}>
        <Definition label="Email" value={user.email || '—'} />
        <Definition label="Joined" value={user.created_at ? fmtRelTime(new Date(user.created_at)) : '—'} />
        <Definition label="Last active" value={user.last_active ? fmtRelTime(new Date(user.last_active)) : '—'} />
        <Definition
          label="Role"
          value={user.is_admin
            ? <StatusChip tone="brand">ADMIN</StatusChip>
            : <StatusChip tone="muted">MEMBER</StatusChip>}
        />
        <Definition
          label="State"
          value={!user.is_active
            ? <StatusChip tone="bear">SUSPENDED</StatusChip>
            : locked
              ? <StatusChip tone="warn">LOCKED</StatusChip>
              : <StatusChip tone="bull">ACTIVE</StatusChip>}
        />
        <Definition
          label="Kite"
          value={user.kite_connected
            ? <StatusChip tone="bull">CONNECTED</StatusChip>
            : <StatusChip tone="muted">OFF</StatusChip>}
        />
        {user.failed_login_attempts > 0 && (
          <Definition label="Failed logins" value={String(user.failed_login_attempts)} />
        )}

        <h3 className="t-ui-micro" style={{ color: 'var(--text-3)', marginTop: 24, marginBottom: 12 }}>
          ACTIONS
        </h3>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {locked && (
            <ActionButton
              icon={<KeyRound size={14} strokeWidth={1.75} />}
              label="Unlock account"
              onClick={() => onAction(user.id, 'unlock', `Unlocked ${user.email}`)}
              disabled={pending}
            />
          )}
          {user.is_active ? (
            <ActionButton
              icon={<X size={14} strokeWidth={1.75} />}
              label="Deactivate user"
              destructive
              onClick={() => onAction(user.id, 'deactivate', `Deactivated ${user.email}`)}
              disabled={pending || user.is_admin}
              hint={user.is_admin ? 'Admins cannot be deactivated' : undefined}
            />
          ) : (
            <ActionButton
              icon={<Check size={14} strokeWidth={1.75} />}
              label="Activate user"
              onClick={() => onAction(user.id, 'activate', `Activated ${user.email}`)}
              disabled={pending}
            />
          )}
          <ActionButton
            icon={<KeyRound size={14} strokeWidth={1.75} />}
            label="Reset password (email link)"
            onClick={() => onAction(user.id, 'reset-password', `Password reset for ${user.email}`)}
            disabled={pending}
          />
          {user.kite_connected && (
            <ActionButton
              icon={<Plug size={14} strokeWidth={1.75} />}
              label="Revoke Kite session"
              destructive
              onClick={() => onAction(user.id, 'revoke-kite', `Revoked Kite for ${user.email}`)}
              disabled={pending}
            />
          )}
        </div>
      </div>
    </SidePanel>
  );
}

// ══════════════════════════════════════════════════════════════
// ACCESS REQUESTS TAB
// ══════════════════════════════════════════════════════════════

function AccessRequestsTab() {
  const [status, setStatus] = useState('pending');
  const requestsQuery = useAdminAccessRequests(status);
  const { approve, reject, remove } = useAdminAccessRequestMutations();

  const requests = requestsQuery.data ?? [];

  return (
    <div style={{ marginTop: 16 }}>
      <div className="flex items-center" style={{ gap: 6, marginBottom: 16 }}>
        {[
          { v: 'pending',  label: 'Pending' },
          { v: 'approved', label: 'Approved' },
          { v: 'rejected', label: 'Rejected' },
          { v: '',         label: 'All' },
        ].map((p) => {
          const active = status === p.v;
          return (
            <button
              key={p.v || 'all'}
              type="button"
              onClick={() => setStatus(p.v)}
              className="t-ui-callout"
              style={{
                padding: '8px 14px',
                background: active ? 'var(--brand-soft)' : 'transparent',
                color: active ? 'var(--brand-hi)' : 'var(--text-2)',
                border: `1px solid ${active ? 'var(--brand-edge)' : 'var(--edge-1)'}`,
                borderRadius: 'var(--r-chip)',
                cursor: 'pointer',
                fontWeight: active ? 600 : 500,
              }}
            >
              {p.label}
            </button>
          );
        })}
      </div>

      {requestsQuery.isLoading ? (
        <CardGridSkeleton count={4} />
      ) : requests.length === 0 ? (
        <ShellCard>
          <EmptyState
            icon={<Inbox />}
            title={`No ${status || 'all'} requests`}
            body="When users submit access requests from the landing page, they appear here."
          />
        </ShellCard>
      ) : (
        <section
          className="grid"
          style={{
            gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 360px), 1fr))',
            gap: 16,
          }}
        >
          {requests.map((r) => (
            <AccessRequestCard
              key={r.id}
              request={r}
              onApprove={async () => {
                try { await approve.mutateAsync({ id: r.id }); toast.success(`Approved ${r.email}`); }
                catch (e) { toast.error(`Approve failed: ${e?.message ?? 'error'}`); }
              }}
              onReject={async () => {
                try { await reject.mutateAsync({ id: r.id }); toast.success(`Rejected ${r.email}`); }
                catch (e) { toast.error(`Reject failed: ${e?.message ?? 'error'}`); }
              }}
              onDelete={async () => {
                if (!window.confirm(`Delete request from ${r.email}? This cannot be undone.`)) return;
                try { await remove.mutateAsync({ id: r.id }); toast.success('Deleted'); }
                catch (e) { toast.error(`Delete failed: ${e?.message ?? 'error'}`); }
              }}
              busy={approve.isPending || reject.isPending || remove.isPending}
            />
          ))}
        </section>
      )}
    </div>
  );
}

function AccessRequestCard({ request, onApprove, onReject, onDelete, busy }) {
  const status = String(request.status || 'pending').toLowerCase();
  const tone = status === 'approved' ? 'bull' : status === 'rejected' ? 'bear' : 'warn';
  return (
    <article
      style={{
        background: 'var(--surface-1)',
        border: '1px solid var(--edge-1)',
        borderRadius: 'var(--r-card)',
        padding: 'var(--pad-card)',
        boxShadow: 'var(--shadow-sm)',
      }}
    >
      <div className="flex items-start justify-between" style={{ gap: 12 }}>
        <div className="min-w-0 flex-1">
          <h3 className="t-title-2" style={{ margin: 0, color: 'var(--text-1)' }}>{request.name}</h3>
          <div className="t-ui-footnote" style={{ color: 'var(--text-3)', marginTop: 2 }}>
            {request.email}
          </div>
        </div>
        <StatusChip tone={tone}>{status.toUpperCase()}</StatusChip>
      </div>

      {request.trading_experience && (
        <div className="t-ui-footnote" style={{ color: 'var(--text-2)', marginTop: 12 }}>
          <span className="t-ui-micro" style={{ color: 'var(--text-3)', marginRight: 6 }}>EXPERIENCE</span>
          {request.trading_experience}
        </div>
      )}
      {request.message && (
        <p
          className="t-ui-body"
          style={{
            color: 'var(--text-2)',
            margin: '12px 0 0',
            display: '-webkit-box',
            WebkitLineClamp: 4,
            WebkitBoxOrient: 'vertical',
            overflow: 'hidden',
          }}
        >
          {request.message}
        </p>
      )}

      <div className="t-ui-footnote" style={{ color: 'var(--text-4)', marginTop: 14 }}>
        Submitted {request.created_at ? fmtRelTime(new Date(request.created_at)) : '—'}
        {request.ip_address ? ` · ${request.ip_address}` : ''}
      </div>

      {status === 'pending' && (
        <div className="flex" style={{ gap: 8, marginTop: 14 }}>
          <button
            type="button"
            disabled={busy}
            onClick={onApprove}
            className="t-ui-callout"
            style={{
              flex: 1,
              padding: '8px 14px',
              background: busy ? 'var(--surface-3)' : 'var(--brand)',
              color: busy ? 'var(--text-3)' : 'var(--brand-fg)',
              border: `1px solid ${busy ? 'var(--edge-1)' : 'var(--brand)'}`,
              borderRadius: 'var(--r-chip)',
              cursor: busy ? 'wait' : 'pointer',
              fontWeight: 600,
            }}
          >
            Approve
          </button>
          <button
            type="button"
            disabled={busy}
            onClick={onReject}
            className="t-ui-callout"
            style={{
              padding: '8px 14px',
              background: 'transparent',
              color: 'var(--text-2)',
              border: '1px solid var(--edge-1)',
              borderRadius: 'var(--r-chip)',
              cursor: busy ? 'wait' : 'pointer',
            }}
          >
            Reject
          </button>
          <button
            type="button"
            aria-label="Delete request"
            disabled={busy}
            onClick={onDelete}
            style={{
              width: 36,
              padding: 8,
              background: 'transparent',
              color: 'var(--bear)',
              border: '1px solid var(--edge-1)',
              borderRadius: 'var(--r-chip)',
              cursor: busy ? 'wait' : 'pointer',
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <Trash2 size={14} strokeWidth={1.75} />
          </button>
        </div>
      )}
    </article>
  );
}

// ══════════════════════════════════════════════════════════════
// SYSTEM TAB — health KPIs + audit log feed
// ══════════════════════════════════════════════════════════════

function SystemTab({ health }) {
  const auditQuery = useAdminAuditLogs({ page: 1, perPage: 50 });
  const kiteRefresh = useAdminRefreshKiteMutation();

  // Array.isArray guard — backend returns `{logs: [...], total, page, pages}`
  // but a stale cached error response or schema drift could leave `data` as
  // an object without `logs`, in which case the previous `?? auditQuery.data`
  // fallback would call `.slice()` on the object and either return garbage
  // or crash. Guard ensures we always render an array (or empty state).
  const audit = Array.isArray(auditQuery.data?.logs)
    ? auditQuery.data.logs.slice(0, 50)
    : [];

  const cron = health?.cron ?? {};
  const kite = health?.kite_owner ?? {};
  const errors = health?.errors_24h ?? 0;

  return (
    <div style={{ marginTop: 16, display: 'flex', flexDirection: 'column', gap: 24 }}>
      <section
        className="grid"
        style={{
          gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
          gap: 16,
        }}
      >
        <DetailCard title="Cron pipeline" icon={<Clock />} tone={cron.status === 'OK' ? 'bull' : 'warn'}>
          <DetailRow label="Status" value={<StatusChip tone={cron.status === 'OK' ? 'bull' : 'warn'}>{cron.status || 'UNKNOWN'}</StatusChip>} />
          <DetailRow label="Last scan" value={cron.scan_time ? fmtRelTime(new Date(cron.scan_time)) : '—'} />
          <DetailRow label="Signals scanned" value={String(cron.n_signals ?? 0)} />
          <DetailRow label="Expected today" value={cron.expected_today != null ? (cron.expected_today ? 'Yes' : 'No') : '—'} />
        </DetailCard>

        <DetailCard
          title="Owner Kite session"
          icon={<Plug />}
          tone={kite.connected ? 'bull' : 'bear'}
          actions={
            <button
              type="button"
              onClick={async () => {
                try { await kiteRefresh.mutateAsync(); toast.success('Kite session refreshed'); }
                catch (e) { toast.error(`Refresh failed: ${e?.message ?? 'error'}`); }
              }}
              disabled={kiteRefresh.isPending}
              className="t-ui-callout"
              style={{
                padding: '6px 12px',
                background: 'transparent',
                color: 'var(--brand-hi)',
                border: '1px solid var(--brand-edge)',
                borderRadius: 'var(--r-chip)',
                cursor: kiteRefresh.isPending ? 'wait' : 'pointer',
                display: 'inline-flex',
                alignItems: 'center',
                gap: 6,
                fontWeight: 600,
              }}
            >
              {kiteRefresh.isPending ? <RefreshCcw size={12} strokeWidth={2} className="animate-spin" /> : <RefreshCcw size={12} strokeWidth={2} />}
              Refresh
            </button>
          }
        >
          <DetailRow label="Status" value={<StatusChip tone={kite.connected ? 'bull' : 'bear'}>{kite.connected ? 'CONNECTED' : 'OFF'}</StatusChip>} />
          <DetailRow label="Kite user ID" value={kite.kite_user_id || '—'} />
          <DetailRow label="Owner email" value={kite.owner_email || '—'} />
          <DetailRow label="Expires" value={kite.expires_at_iso ? new Date(kite.expires_at_iso).toLocaleString('en-IN') : '—'} />
        </DetailCard>

        <DetailCard
          title="Backend"
          icon={<Database />}
          tone={errors > 5 ? 'warn' : errors > 0 ? 'neutral' : 'bull'}
        >
          <DetailRow label="Errors (24h)" value={String(errors)} />
          <DetailRow label="Server UTC" value={health?.server_time?.utc ? new Date(health.server_time.utc).toLocaleTimeString('en-IN') : '—'} />
          <DetailRow label="Server IST" value={health?.server_time?.ist ? new Date(health.server_time.ist).toLocaleTimeString('en-IN') : '—'} />
        </DetailCard>
      </section>

      {/* AUDIT LOG */}
      <section>
        <h2 className="t-title-2" style={{ margin: '0 0 12px', color: 'var(--text-1)' }}>
          Audit log
        </h2>
        {auditQuery.isLoading ? (
          <TableSkeleton rows={6} cols={4} />
        ) : audit.length === 0 ? (
          <ShellCard>
            <EmptyState icon={<Activity />} title="No audit entries" body="Recent admin actions and security events will appear here." />
          </ShellCard>
        ) : (
          <DataTable
            rows={audit.map((a, i) => ({ id: a.id ?? i, ...a }))}
            initialSort={{ key: 'timestamp', dir: 'desc' }}
            columns={[
              {
                key: 'timestamp',
                header: 'When',
                sortable: true,
                width: '160px',
                render: (v) => v ? fmtRelTime(new Date(v)) : '—',
              },
              {
                key: 'action',
                header: 'Action',
                sortable: true,
                width: '200px',
                render: (v) => {
                  const u = String(v || '').toUpperCase();
                  const failed = /FAILED|ERROR|REJECTED|REVOKED/i.test(u);
                  return (
                    <StatusChip tone={failed ? 'bear' : u.includes('LOGIN') ? 'info' : 'muted'}>
                      {u.replace(/_/g, ' ')}
                    </StatusChip>
                  );
                },
              },
              { key: 'user_email', header: 'Actor', sortable: true, width: '220px', render: (_, a) => a.user_email || a.user_id || '—' },
              {
                key: 'detail',
                header: 'Detail',
                render: (v) => (
                  <span className="t-ui-footnote" style={{ color: 'var(--text-2)' }}>{v || '—'}</span>
                ),
              },
              { key: 'ip_address', header: 'IP', width: '140px' },
            ]}
          />
        )}
      </section>
    </div>
  );
}

// ══════════════════════════════════════════════════════════════
// OPERATIONS TAB — manual actions
// ══════════════════════════════════════════════════════════════

function OperationsTab() {
  const runScan = useAdminRunScanMutation();
  const refreshKite = useAdminRefreshKiteMutation();

  const [scanResult, setScanResult] = useState(null);
  const [kiteResult, setKiteResult] = useState(null);

  const handleRunScan = async () => {
    if (!window.confirm('Run signal scan now? This calls cron_runner outside the schedule.')) return;
    try {
      const res = await runScan.mutateAsync();
      setScanResult({ when: new Date(), data: res });
      toast.success('Signal scan triggered');
    } catch (e) {
      toast.error(`Scan failed: ${e?.message ?? 'unknown error'}`);
    }
  };

  const handleRefreshKite = async () => {
    if (!window.confirm('Refresh owner Kite session? This will TOTP-rotate the access token.')) return;
    try {
      const res = await refreshKite.mutateAsync();
      setKiteResult({ when: new Date(), data: res });
      toast.success('Owner Kite session refreshed');
    } catch (e) {
      toast.error(`Refresh failed: ${e?.message ?? 'unknown error'}`);
    }
  };

  return (
    <div style={{ marginTop: 16, display: 'flex', flexDirection: 'column', gap: 16 }}>
      <OperationCard
        icon={<Zap size={18} strokeWidth={1.75} />}
        title="Run signal scan now"
        description="Forces cron_runner to execute outside the 4:15 PM IST schedule. Scans all 441 tradeable Nifty 500 tickers, generates v1 LightGBM predictions, applies the 0.92 confidence gate, writes signals_today.json + signals_history.json, and pushes to GitHub."
        ctaLabel={runScan.isPending ? 'Scanning…' : 'Run scan'}
        onClick={handleRunScan}
        disabled={runScan.isPending}
        result={scanResult}
        warning="Triggers ~100 yfinance calls. Don't run more than once per hour."
      />

      <OperationCard
        icon={<RefreshCcw size={18} strokeWidth={1.75} />}
        title="Refresh owner Kite session"
        description="Performs the same TOTP-based Kite OAuth flow as the daily 6 AM IST cron — fetches a new access_token using the saved password + TOTP secret. Use when the owner session expired and quotes / live data went down for everyone."
        ctaLabel={refreshKite.isPending ? 'Refreshing…' : 'Refresh now'}
        onClick={handleRefreshKite}
        disabled={refreshKite.isPending}
        result={kiteResult}
      />

      <div
        style={{
          padding: '14px 18px',
          background: 'var(--info-soft)',
          border: '1px solid oklch(78% 0.11 230 / 0.32)',
          borderRadius: 'var(--r-chip)',
          color: 'var(--text-2)',
        }}
      >
        <p className="t-ui-body" style={{ margin: 0 }}>
          More operations (push strategy update, trigger backtest, broadcast announcement) ship in a future release. They'll need explicit backend endpoints first.
        </p>
      </div>
    </div>
  );
}

function OperationCard({ icon, title, description, ctaLabel, onClick, disabled, result, warning }) {
  return (
    <div
      style={{
        background: 'var(--surface-1)',
        border: '1px solid var(--edge-1)',
        borderRadius: 'var(--r-card)',
        padding: 'var(--pad-card)',
        boxShadow: 'var(--shadow-sm)',
      }}
    >
      <div className="flex items-start" style={{ gap: 14 }}>
        <div
          className="flex items-center justify-center flex-shrink-0"
          style={{
            width: 36, height: 36,
            borderRadius: 'var(--r-chip)',
            background: 'var(--surface-3)',
            border: '1px solid var(--edge-1)',
            color: 'var(--brand-hi)',
          }}
        >
          {icon}
        </div>
        <div className="min-w-0 flex-1">
          <h3 className="t-title-2" style={{ margin: 0, color: 'var(--text-1)' }}>{title}</h3>
          <p className="t-ui-body" style={{ color: 'var(--text-2)', margin: '6px 0 0', maxWidth: '70ch' }}>
            {description}
          </p>
          {warning && (
            <p
              className="t-ui-footnote"
              style={{
                color: 'var(--warn)',
                margin: '8px 0 0',
                paddingLeft: 8,
                borderLeft: '2px solid var(--warn)',
              }}
            >
              {warning}
            </p>
          )}
          {result && (
            <pre
              style={{
                marginTop: 12,
                padding: 12,
                background: 'var(--surface-2)',
                border: '1px solid var(--edge-1)',
                borderRadius: 'var(--r-chip)',
                fontFamily: 'var(--font-mono)',
                fontSize: 11,
                color: 'var(--text-2)',
                overflowX: 'auto',
                maxHeight: 200,
              }}
            >
              {`Last run: ${result.when.toLocaleString('en-IN')}\n` + JSON.stringify(result.data, null, 2)}
            </pre>
          )}
        </div>
        <button
          type="button"
          onClick={onClick}
          disabled={disabled}
          className="t-ui-callout"
          style={{
            padding: '10px 18px',
            background: disabled ? 'var(--surface-3)' : 'var(--brand)',
            color: disabled ? 'var(--text-3)' : 'var(--brand-fg)',
            border: `1px solid ${disabled ? 'var(--edge-1)' : 'var(--brand)'}`,
            borderRadius: 'var(--r-chip)',
            cursor: disabled ? 'wait' : 'pointer',
            fontWeight: 600,
            flexShrink: 0,
          }}
        >
          {ctaLabel}
        </button>
      </div>
    </div>
  );
}

// ══════════════════════════════════════════════════════════════
// SHARED — table skeleton, definition row, action button, side panel
// ══════════════════════════════════════════════════════════════

function TabStrip({ tabs, active, onChange }) {
  return (
    <div role="tablist" className="flex items-center" style={{ borderBottom: '1px solid var(--edge-1)' }}>
      {tabs.map((t) => {
        const isActive = t.value === active;
        const Icon = t.icon;
        return (
          <button
            key={t.value}
            type="button"
            role="tab"
            aria-selected={isActive}
            onClick={() => onChange(t.value)}
            className="t-ui-subhead"
            style={{
              padding: '12px 16px',
              background: 'transparent',
              color: isActive ? 'var(--text-1)' : 'var(--text-3)',
              border: 'none',
              borderBottom: `2px solid ${isActive ? 'var(--brand)' : 'transparent'}`,
              marginBottom: -1,
              cursor: 'pointer',
              fontWeight: isActive ? 600 : 500,
              display: 'inline-flex',
              alignItems: 'center',
              gap: 8,
              transition: 'color var(--dur-hover), border-color var(--dur-hover)',
            }}
          >
            {Icon && <Icon size={14} strokeWidth={1.75} />}
            {t.label}
          </button>
        );
      })}
    </div>
  );
}

function Definition({ label, value }) {
  return (
    <div
      className="flex items-baseline justify-between"
      style={{
        padding: '10px 0',
        borderBottom: '1px solid var(--edge-1)',
        gap: 12,
      }}
    >
      <span className="t-ui-footnote" style={{ color: 'var(--text-3)' }}>{label}</span>
      {React.isValidElement(value)
        ? value
        : <span className="t-num-body" style={{ color: 'var(--text-1)' }}>{value}</span>}
    </div>
  );
}

function DetailCard({ title, icon, tone, actions, children }) {
  const accent =
    tone === 'bull' ? 'var(--bull)' :
    tone === 'bear' ? 'var(--bear)' :
    tone === 'warn' ? 'var(--warn)' :
    'var(--text-3)';
  return (
    <div
      style={{
        background: 'var(--surface-1)',
        border: '1px solid var(--edge-1)',
        borderRadius: 'var(--r-card)',
        boxShadow: 'var(--shadow-sm)',
        overflow: 'hidden',
      }}
    >
      <header
        className="flex items-center justify-between"
        style={{
          padding: '14px 18px',
          borderBottom: '1px solid var(--edge-1)',
          gap: 12,
        }}
      >
        <div className="flex items-center" style={{ gap: 10 }}>
          <span style={{ color: accent }}>{icon}</span>
          <h3 className="t-title-2" style={{ margin: 0, color: 'var(--text-1)' }}>{title}</h3>
        </div>
        {actions}
      </header>
      <div style={{ padding: '8px 18px 14px' }}>{children}</div>
    </div>
  );
}

function DetailRow({ label, value }) {
  return (
    <div
      className="flex items-baseline justify-between"
      style={{ padding: '8px 0', borderBottom: '1px solid var(--edge-1)' }}
    >
      <span className="t-ui-footnote" style={{ color: 'var(--text-3)' }}>{label}</span>
      {React.isValidElement(value)
        ? value
        : <span className="t-num-body" style={{ color: 'var(--text-1)' }}>{value}</span>}
    </div>
  );
}

function ActionButton({ icon, label, hint, onClick, disabled, destructive }) {
  return (
    <div>
      <button
        type="button"
        onClick={onClick}
        disabled={disabled}
        className="t-ui-callout"
        style={{
          width: '100%',
          padding: '10px 14px',
          background: 'transparent',
          color: destructive ? 'var(--bear)' : 'var(--text-1)',
          border: `1px solid ${destructive ? 'var(--bear)' : 'var(--edge-2)'}`,
          borderRadius: 'var(--r-chip)',
          cursor: disabled ? 'not-allowed' : 'pointer',
          opacity: disabled ? 0.5 : 1,
          display: 'inline-flex',
          alignItems: 'center',
          gap: 8,
          fontWeight: 500,
        }}
      >
        {icon}
        {label}
      </button>
      {hint && (
        <div className="t-ui-footnote" style={{ color: 'var(--text-4)', margin: '4px 0 0', paddingLeft: 4 }}>
          {hint}
        </div>
      )}
    </div>
  );
}

function SidePanel({ open, onOpenChange, title, children }) {
  if (!open) return null;
  return (
    <>
      <div
        onClick={() => onOpenChange(false)}
        style={{
          position: 'fixed', inset: 0, zIndex: 49,
          background: 'oklch(0% 0 0 / 0.6)',
          backdropFilter: 'blur(4px)',
        }}
      />
      <aside
        role="dialog"
        aria-label={title}
        style={{
          position: 'fixed', top: 0, right: 0, bottom: 0, zIndex: 50,
          width: 'min(440px, 100vw)',
          background: 'var(--surface-modal)',
          backdropFilter: 'blur(24px)',
          WebkitBackdropFilter: 'blur(24px)',
          borderLeft: '1px solid var(--edge-2)',
          boxShadow: 'var(--shadow-lg)',
          overflowY: 'auto',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        <header
          className="flex items-center justify-between"
          style={{
            padding: '20px 24px',
            borderBottom: '1px solid var(--edge-1)',
            flexShrink: 0,
          }}
        >
          <h2 className="t-title-2" style={{ margin: 0, color: 'var(--text-1)' }}>{title}</h2>
          <button
            type="button"
            onClick={() => onOpenChange(false)}
            aria-label="Close"
            style={{
              background: 'transparent',
              border: 'none',
              cursor: 'pointer',
              color: 'var(--text-3)',
              padding: 4,
            }}
          >
            <X size={18} strokeWidth={1.75} />
          </button>
        </header>
        <div className="flex-1">{children}</div>
      </aside>
    </>
  );
}

function ShellCard({ children }) {
  return (
    <div
      style={{
        background: 'var(--surface-1)',
        border: '1px solid var(--edge-1)',
        borderRadius: 'var(--r-card)',
        minHeight: 280,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      {children}
    </div>
  );
}

function TableSkeleton({ rows = 6, cols = 5 }) {
  return (
    <div
      style={{
        background: 'var(--surface-1)',
        border: '1px solid var(--edge-1)',
        borderRadius: 'var(--r-card)',
        padding: 16,
        animation: 'skelPulse 1.8s ease-in-out infinite',
      }}
    >
      {Array.from({ length: rows }).map((_, i) => (
        <div
          key={i}
          style={{
            height: 40,
            display: 'grid',
            gridTemplateColumns: `repeat(${cols}, 1fr)`,
            gap: 12,
            alignItems: 'center',
            borderBottom: i === rows - 1 ? 'none' : '1px solid var(--edge-1)',
          }}
        >
          {Array.from({ length: cols }).map((__, j) => (
            <div key={j} style={{ height: 12, background: 'var(--surface-2)', borderRadius: 4 }} />
          ))}
        </div>
      ))}
      <style>{`@keyframes skelPulse { 0%, 100% { opacity: 1 } 50% { opacity: 0.6 } }`}</style>
    </div>
  );
}

function CardGridSkeleton({ count = 4 }) {
  return (
    <section
      className="grid"
      style={{
        gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 360px), 1fr))',
        gap: 16,
      }}
    >
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          style={{
            background: 'var(--surface-1)',
            border: '1px solid var(--edge-1)',
            borderRadius: 'var(--r-card)',
            minHeight: 200,
            animation: 'skelPulse 1.8s ease-in-out infinite',
          }}
        />
      ))}
      <style>{`@keyframes skelPulse { 0%, 100% { opacity: 1 } 50% { opacity: 0.6 } }`}</style>
    </section>
  );
}
