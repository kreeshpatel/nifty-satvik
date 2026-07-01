import React, { useState, useEffect, useContext } from 'react';
import { Header } from '@/components/layout/Header';
import { AuthContext } from '@/context/AuthContext';
import { Navigate } from 'react-router-dom';

const API = process.env.REACT_APP_API_URL ?? '';

const authFetch = (url, options = {}) =>
  fetch(url, { ...options, credentials: 'include' });

// Read response as text first then parse, to avoid "body stream already read" errors
const safeJson = async (res) => {
  const text = await res.text();
  try {
    return text ? JSON.parse(text) : {};
  } catch {
    return {};
  }
};

const authJson = (url) => authFetch(url).then(safeJson);

export default function Admin() {
  const { user } = useContext(AuthContext);
  const [users, setUsers] = useState([]);
  const [logs, setLogs] = useState([]);
  const [logsPage, setLogsPage] = useState(1);
  const [logsTotal, setLogsTotal] = useState(0);
  const [tab, setTab] = useState('users');
  const [showCreateUser, setShowCreateUser] = useState(false);
  const [newUser, setNewUser] = useState({ email: '', password: '', name: '' });
  const [message, setMessage] = useState('');
  const [kiteStatus, setKiteStatus] = useState(null);
  const [refreshing, setRefreshing] = useState(false);
  const [accessRequests, setAccessRequests] = useState([]);
  const [approvingId, setApprovingId] = useState(null);
  const [approvePassword, setApprovePassword] = useState('');

  const loadUsers = () =>
    authJson(`${API}/api/admin/users`)
      .then(data => setUsers(Array.isArray(data) ? data : []))
      .catch(() => setUsers([]));

  const loadLogs = (page = 1) =>
    authJson(`${API}/api/admin/audit-logs?page=${page}&per_page=25`)
      .then(data => {
        setLogs(Array.isArray(data?.logs) ? data.logs : []);
        setLogsTotal(data?.total || 0);
        setLogsPage(page);
      })
      .catch(() => setLogs([]));

  const loadKiteStatus = () =>
    authJson(`${API}/api/admin/kite-status`)
      .then(setKiteStatus)
      .catch(() => setKiteStatus(null));

  const loadAccessRequests = () =>
    authJson(`${API}/api/admin/access-requests?per_page=50`)
      .then(data => setAccessRequests(Array.isArray(data?.requests) ? data.requests : []))
      .catch(() => setAccessRequests([]));

  const approveRequest = async (id) => {
    if (!approvePassword || approvePassword.length < 6) {
      setMessage('Password must be at least 6 characters');
      setTimeout(() => setMessage(''), 5000);
      return;
    }
    try {
      const res = await authFetch(`${API}/api/admin/access-requests/${id}/approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password: approvePassword }),
      });
      const data = await safeJson(res);
      if (res.ok) {
        setMessage(`User created: ${data.email}. Share this password securely: ${approvePassword}`);
        setApprovingId(null);
        setApprovePassword('');
        loadAccessRequests();
        loadUsers();
      } else {
        setMessage(`Error: ${data.detail || 'Approval failed'}`);
      }
    } catch (err) {
      setMessage(`Network error: ${err.message}`);
    }
    setTimeout(() => setMessage(''), 12000);
  };

  const rejectRequest = async (id) => {
    try {
      await authFetch(`${API}/api/admin/access-requests/${id}/reject`, { method: 'POST' });
      setMessage('Request rejected');
      loadAccessRequests();
    } catch {
      setMessage('Failed to reject');
    }
    setTimeout(() => setMessage(''), 5000);
  };

  const deleteRequest = async (id) => {
    try {
      await authFetch(`${API}/api/admin/access-requests/${id}`, { method: 'DELETE' });
      setMessage('Request deleted');
      loadAccessRequests();
    } catch {
      setMessage('Failed to delete');
    }
    setTimeout(() => setMessage(''), 5000);
  };

  const refreshKiteSession = async () => {
    setRefreshing(true);
    setMessage('Refreshing Kite session...');
    try {
      const res = await authFetch(`${API}/api/admin/refresh-kite`, { method: 'POST' });
      const data = await safeJson(res);
      if (res.ok) {
        setMessage(`Kite session refreshed for ${data.kite_user_id}`);
        loadKiteStatus();
      } else {
        setMessage(`Error: ${data.detail || 'Refresh failed'}`);
      }
    } catch (err) {
      setMessage(`Network error: ${err.message}`);
    }
    setRefreshing(false);
    setTimeout(() => setMessage(''), 8000);
  };

  useEffect(() => {
    if (user?.is_admin) {
      loadUsers();
      loadLogs();
      loadKiteStatus();
      loadAccessRequests();
    }
  }, [user]);

  if (!user?.is_admin) return <Navigate to="/" replace />;

  const doAction = async (url, label) => {
    try {
      const res = await authFetch(url, { method: 'POST' });
      const data = await safeJson(res);
      if (data.temp_password) {
        setMessage(`Temp password: ${data.temp_password}`);
      } else {
        setMessage(data.message || data.detail || label);
      }
      loadUsers();
    } catch (err) {
      setMessage(`Error: ${err.message}`);
    }
    setTimeout(() => setMessage(''), 8000);
  };

  const createUser = async (e) => {
    e.preventDefault();
    e.stopPropagation();
    setMessage('Creating user...');
    try {
      const res = await authFetch(`${API}/api/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newUser),
      });
      const data = await safeJson(res);
      if (res.ok) {
        setMessage(`User ${data.email} created`);
        setShowCreateUser(false);
        setNewUser({ email: '', password: '', name: '' });
        loadUsers();
      } else {
        setMessage(`Error ${res.status}: ${data.detail || 'Failed to create user'}`);
      }
    } catch (err) {
      setMessage(`Network error: ${err.message}`);
    }
    setTimeout(() => setMessage(''), 8000);
  };

  return (
    <div className="p-6 space-y-6 max-w-6xl">
      <Header title="Admin Panel" subtitle="Manage users, sessions & audit logs" />

      {message && (
        <div className="rounded-md bg-primary/10 border border-primary/20 px-4 py-2 text-sm text-primary">
          {message}
        </div>
      )}

      {/* Owner Kite Session Status Card */}
      <div className="rounded-xl border bg-card p-4">
        <div className="flex items-center justify-between gap-4">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1">
              <h3 className="text-sm font-semibold">Market Data — Kite Session</h3>
              {kiteStatus?.connected ? (
                <span className="text-xs text-green-400 bg-green-400/10 px-2 py-0.5 rounded">Active</span>
              ) : (
                <span className="text-xs text-red-400 bg-red-400/10 px-2 py-0.5 rounded">Expired</span>
              )}
            </div>
            <p className="text-xs text-muted-foreground">
              {kiteStatus?.connected ? (
                <>
                  Powering live data for all users via Kite ID{' '}
                  <span className="text-foreground font-mono">{kiteStatus.kite_user_id}</span>.
                  {' '}Expires{' '}
                  <span className="text-foreground">
                    {kiteStatus.expires_at_iso ? new Date(kiteStatus.expires_at_iso).toLocaleString() : 'unknown'}
                  </span>
                  . Auto-refreshed daily at ~6:15 AM IST.
                </>
              ) : (
                <>Owner's Kite session is expired or not connected. Users cannot see live market data until refreshed.</>
              )}
            </p>
          </div>
          <button
            onClick={refreshKiteSession}
            disabled={refreshing}
            className="px-4 py-2 rounded-lg text-sm font-medium bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 whitespace-nowrap"
          >
            {refreshing ? 'Refreshing...' : 'Refresh Now'}
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-2">
        {[
          { key: 'users', label: 'Users' },
          { key: 'requests', label: `Access Requests${accessRequests.filter(r => r.status === 'pending').length > 0 ? ` (${accessRequests.filter(r => r.status === 'pending').length})` : ''}` },
          { key: 'audit', label: 'Audit Logs' },
        ].map(t => (
          <button
            key={t.key}
            onClick={() => { setTab(t.key); if (t.key === 'audit') loadLogs(1); if (t.key === 'requests') loadAccessRequests(); }}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              tab === t.key ? 'bg-primary text-primary-foreground' : 'bg-card text-muted-foreground hover:text-foreground'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Users Tab */}
      {tab === 'users' && (
        <div className="space-y-4">
          <button
            onClick={() => setShowCreateUser(!showCreateUser)}
            className="px-4 py-2 rounded-lg text-sm font-medium bg-primary text-primary-foreground hover:bg-primary/90"
          >
            + Create User
          </button>

          {showCreateUser && (
            <form onSubmit={createUser} className="rounded-xl border bg-card p-4 space-y-3 max-w-md">
              <input
                type="text" placeholder="Name" required value={newUser.name}
                onChange={e => setNewUser({ ...newUser, name: e.target.value })}
                className="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm"
              />
              <input
                type="email" placeholder="Email" required value={newUser.email}
                onChange={e => setNewUser({ ...newUser, email: e.target.value })}
                className="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm"
              />
              <input
                type="text" placeholder="Password" required value={newUser.password}
                onChange={e => setNewUser({ ...newUser, password: e.target.value })}
                className="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm"
              />
              <button type="submit" className="px-4 py-2 rounded-lg text-sm bg-primary text-primary-foreground">
                Create
              </button>
            </form>
          )}

          <div className="rounded-xl border bg-card overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-muted-foreground text-left">
                  <th className="p-3">User</th>
                  <th className="p-3">Status</th>
                  <th className="p-3">Kite</th>
                  <th className="p-3">Last Active</th>
                  <th className="p-3">Actions</th>
                </tr>
              </thead>
              <tbody>
                {users.map(u => (
                  <tr key={u.id} className="border-b last:border-0">
                    <td className="p-3">
                      <div className="font-medium">{u.name}</div>
                      <div className="text-xs text-muted-foreground">{u.email}</div>
                      {u.is_admin && <span className="text-xs text-amber-500">Admin</span>}
                    </td>
                    <td className="p-3">
                      {u.locked_until ? (
                        <span className="text-xs text-red-400 bg-red-400/10 px-2 py-0.5 rounded">Locked</span>
                      ) : u.is_active ? (
                        <span className="text-xs text-green-400 bg-green-400/10 px-2 py-0.5 rounded">Active</span>
                      ) : (
                        <span className="text-xs text-gray-400 bg-gray-400/10 px-2 py-0.5 rounded">Inactive</span>
                      )}
                    </td>
                    <td className="p-3">
                      {u.kite_connected ? (
                        <span className="text-xs text-green-400">{u.kite_user_id}</span>
                      ) : (
                        <span className="text-xs text-muted-foreground">Not connected</span>
                      )}
                    </td>
                    <td className="p-3 text-xs text-muted-foreground">
                      {u.last_active ? new Date(u.last_active).toLocaleString() : 'Never'}
                    </td>
                    <td className="p-3">
                      <div className="flex gap-1 flex-wrap">
                        {u.locked_until && (
                          <ActionBtn label="Unlock" onClick={() => doAction(`${API}/api/admin/users/${u.id}/unlock`, 'Unlocked')} />
                        )}
                        {u.is_active ? (
                          <ActionBtn label="Deactivate" danger onClick={() => doAction(`${API}/api/admin/users/${u.id}/deactivate`, 'Deactivated')} />
                        ) : (
                          <ActionBtn label="Activate" onClick={() => doAction(`${API}/api/admin/users/${u.id}/activate`, 'Activated')} />
                        )}
                        <ActionBtn label="Reset PW" onClick={() => doAction(`${API}/api/admin/users/${u.id}/reset-password`, 'Password reset')} />
                        {u.kite_connected && (
                          <ActionBtn label="Revoke Kite" danger onClick={() => doAction(`${API}/api/admin/users/${u.id}/revoke-kite`, 'Kite revoked')} />
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Access Requests Tab */}
      {tab === 'requests' && (
        <div className="space-y-4">
          {accessRequests.length === 0 ? (
            <div className="rounded-xl border bg-card p-8 text-center">
              <p className="text-sm text-muted-foreground">No access requests yet.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {accessRequests.map(req => {
                const isPending = req.status === 'pending';
                const isApproving = approvingId === req.id;
                return (
                  <div key={req.id} className="rounded-xl border bg-card p-4">
                    <div className="flex items-start justify-between gap-4 flex-wrap">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <h3 className="text-sm font-semibold">{req.name}</h3>
                          <span className={`text-xs px-2 py-0.5 rounded ${
                            isPending ? 'bg-amber-400/10 text-amber-400' :
                            req.status === 'approved' ? 'bg-green-400/10 text-green-400' :
                            'bg-red-400/10 text-red-400'
                          }`}>
                            {req.status}
                          </span>
                        </div>
                        <p className="text-xs text-muted-foreground mb-2">{req.email}</p>
                        {req.trading_experience && (
                          <p className="text-xs text-muted-foreground mb-1">
                            <span className="font-medium">Experience:</span> {req.trading_experience}
                          </p>
                        )}
                        {req.message && (
                          <p className="text-xs text-foreground/80 mt-2 max-w-2xl">{req.message}</p>
                        )}
                        <p className="text-[10px] text-muted-foreground mt-2">
                          Submitted {req.created_at ? new Date(req.created_at).toLocaleString() : '-'}
                          {req.ip_address && ` from ${req.ip_address}`}
                        </p>
                      </div>
                      {isPending && (
                        <div className="flex flex-col gap-2 items-end">
                          {isApproving ? (
                            <div className="flex flex-col gap-2 w-64">
                              <input
                                type="text"
                                placeholder="Set password for new user"
                                value={approvePassword}
                                onChange={e => setApprovePassword(e.target.value)}
                                className="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm"
                                autoFocus
                              />
                              <div className="flex gap-2">
                                <button
                                  onClick={() => approveRequest(req.id)}
                                  className="px-3 py-1.5 rounded text-xs font-semibold bg-green-500/15 text-green-400 hover:bg-green-500/25"
                                >
                                  Confirm Approve
                                </button>
                                <button
                                  onClick={() => { setApprovingId(null); setApprovePassword(''); }}
                                  className="px-3 py-1.5 rounded text-xs text-muted-foreground hover:text-foreground"
                                >
                                  Cancel
                                </button>
                              </div>
                            </div>
                          ) : (
                            <div className="flex gap-2">
                              <button
                                onClick={() => { setApprovingId(req.id); setApprovePassword(''); }}
                                className="px-3 py-1.5 rounded text-xs font-semibold bg-green-500/15 text-green-400 hover:bg-green-500/25"
                              >
                                Approve
                              </button>
                              <button
                                onClick={() => rejectRequest(req.id)}
                                className="px-3 py-1.5 rounded text-xs font-semibold bg-red-500/10 text-red-400 hover:bg-red-500/20"
                              >
                                Reject
                              </button>
                            </div>
                          )}
                        </div>
                      )}
                      {!isPending && (
                        <button
                          onClick={() => deleteRequest(req.id)}
                          className="px-2 py-1 rounded text-xs text-muted-foreground hover:text-red-400"
                        >
                          Delete
                        </button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Audit Logs Tab */}
      {tab === 'audit' && (
        <div className="space-y-4">
          <div className="rounded-xl border bg-card overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-muted-foreground text-left">
                  <th className="p-3">Time</th>
                  <th className="p-3">Action</th>
                  <th className="p-3">User ID</th>
                  <th className="p-3">Detail</th>
                  <th className="p-3">IP</th>
                </tr>
              </thead>
              <tbody>
                {logs.map(log => (
                  <tr key={log.id} className="border-b last:border-0">
                    <td className="p-3 text-xs text-muted-foreground whitespace-nowrap">
                      {log.timestamp ? new Date(log.timestamp).toLocaleString() : '-'}
                    </td>
                    <td className="p-3">
                      <span className={`text-xs px-2 py-0.5 rounded ${
                        log.action.includes('FAIL') || log.action.includes('LOCK') ? 'bg-red-400/10 text-red-400' :
                        log.action.includes('SUCCESS') || log.action.includes('CREATED') ? 'bg-green-400/10 text-green-400' :
                        'bg-blue-400/10 text-blue-400'
                      }`}>
                        {log.action}
                      </span>
                    </td>
                    <td className="p-3 text-xs">{log.user_id || '-'}</td>
                    <td className="p-3 text-xs text-muted-foreground max-w-xs truncate">{log.detail || '-'}</td>
                    <td className="p-3 text-xs text-muted-foreground">{log.ip_address || '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="flex gap-2 justify-center">
            <button
              onClick={() => loadLogs(logsPage - 1)}
              disabled={logsPage <= 1}
              className="px-3 py-1 rounded text-xs bg-card border disabled:opacity-30"
            >
              Prev
            </button>
            <span className="text-xs text-muted-foreground py-1">Page {logsPage}</span>
            <button
              onClick={() => loadLogs(logsPage + 1)}
              disabled={logs.length < 25}
              className="px-3 py-1 rounded text-xs bg-card border disabled:opacity-30"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function ActionBtn({ label, onClick, danger }) {
  return (
    <button
      onClick={onClick}
      className={`px-2 py-1 rounded text-xs font-medium transition-colors ${
        danger
          ? 'text-red-400 hover:bg-red-400/10'
          : 'text-primary hover:bg-primary/10'
      }`}
    >
      {label}
    </button>
  );
}
