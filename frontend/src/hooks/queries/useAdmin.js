/**
 * Admin query + mutation hooks. All endpoints require is_admin=true on the
 * authenticated user; the backend rejects with 403 otherwise. The hooks
 * themselves don't gate on the role — that's enforced by routing the
 * admin page behind `user.is_admin` in App.js.
 *
 * Cache policy:
 *   - Users + access requests: 60s stale (state changes when admin acts)
 *   - Audit logs: 30s stale (high-frequency append-only)
 *   - System health: 30s stale + refetch on focus (used in hero strip)
 *   - Kite status: 60s stale (changes hourly at most)
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  adminListUsers,
  adminCreateUser,
  adminUserAction,
  adminAuditLogs,
  adminKiteStatus,
  adminRefreshKite,
  adminSystemHealth,
  adminListAccessRequests,
  adminApproveAccessRequest,
  adminRejectAccessRequest,
  adminDeleteAccessRequest,
  runSignalScan,
} from '@/services/api';

export const ADMIN_USERS_KEY = ['admin', 'users'];
export const ADMIN_AUDIT_KEY = ['admin', 'audit'];
export const ADMIN_KITE_KEY = ['admin', 'kite-status'];
export const ADMIN_HEALTH_KEY = ['admin', 'system-health'];
export const ADMIN_ACCESS_KEY = ['admin', 'access-requests'];

// ── Queries ──────────────────────────────────────────────

export function useAdminUsers(opts = {}) {
  return useQuery({
    queryKey: ADMIN_USERS_KEY,
    queryFn: adminListUsers,
    staleTime: 60 * 1000,
    gcTime: 10 * 60 * 1000,
    select: (raw) => (Array.isArray(raw) ? raw : raw?.users ?? []),
    ...opts,
  });
}

export function useAdminAuditLogs({ page = 1, perPage = 50, action } = {}, opts = {}) {
  return useQuery({
    queryKey: [...ADMIN_AUDIT_KEY, { page, perPage, action: action ?? null }],
    queryFn: () => adminAuditLogs({ page, perPage, action }),
    staleTime: 30 * 1000,
    gcTime: 10 * 60 * 1000,
    ...opts,
  });
}

export function useAdminKiteStatus(opts = {}) {
  return useQuery({
    queryKey: ADMIN_KITE_KEY,
    queryFn: adminKiteStatus,
    staleTime: 60 * 1000,
    gcTime: 10 * 60 * 1000,
    ...opts,
  });
}

export function useAdminSystemHealth(opts = {}) {
  return useQuery({
    queryKey: ADMIN_HEALTH_KEY,
    queryFn: adminSystemHealth,
    staleTime: 30 * 1000,
    gcTime: 10 * 60 * 1000,
    refetchOnWindowFocus: true,
    refetchInterval: 60 * 1000,
    ...opts,
  });
}

export function useAdminAccessRequests(status, opts = {}) {
  return useQuery({
    queryKey: [...ADMIN_ACCESS_KEY, status ?? 'all'],
    queryFn: () => adminListAccessRequests(status),
    staleTime: 60 * 1000,
    gcTime: 10 * 60 * 1000,
    // Backend confirmed shape: `{requests: [...], total, page, pages}`.
    // Bare-array fallback covers the (unlikely) future direct-array shape;
    // the dead `raw?.data` fallback was removed during the audit sweep.
    select: (raw) => (Array.isArray(raw) ? raw : Array.isArray(raw?.requests) ? raw.requests : []),
    ...opts,
  });
}

// ── Mutations ────────────────────────────────────────────

/**
 * useAdminUserMutation — single mutation hook covering deactivate / activate /
 * unlock / reset-password / revoke-kite. Caller passes { userId, action }.
 * Invalidates the users list + system health on success.
 */
export function useAdminUserMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ userId, action }) => adminUserAction(userId, action),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ADMIN_USERS_KEY });
      qc.invalidateQueries({ queryKey: ADMIN_HEALTH_KEY });
    },
  });
}

/**
 * useAdminCreateUserMutation — create a new login via POST /api/auth/register.
 * Caller passes { name, email, password }. Invalidates the users list +
 * system health so the new row + counts show up immediately.
 */
export function useAdminCreateUserMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ name, email, password }) => adminCreateUser({ name, email, password }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ADMIN_USERS_KEY });
      qc.invalidateQueries({ queryKey: ADMIN_HEALTH_KEY });
    },
  });
}

export function useAdminRefreshKiteMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: adminRefreshKite,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ADMIN_KITE_KEY });
      qc.invalidateQueries({ queryKey: ADMIN_HEALTH_KEY });
    },
  });
}

export function useAdminRunScanMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: runSignalScan,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ADMIN_HEALTH_KEY });
      // /signals will return new data after a successful scan
      qc.invalidateQueries({ queryKey: ['signals'] });
    },
  });
}

export function useAdminAccessRequestMutations() {
  const qc = useQueryClient();
  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ADMIN_ACCESS_KEY });
    qc.invalidateQueries({ queryKey: ADMIN_HEALTH_KEY });
    qc.invalidateQueries({ queryKey: ADMIN_USERS_KEY });
  };
  return {
    approve: useMutation({
      mutationFn: ({ id, payload }) => adminApproveAccessRequest(id, payload ?? {}),
      onSuccess: invalidate,
    }),
    reject: useMutation({
      mutationFn: ({ id }) => adminRejectAccessRequest(id),
      onSuccess: invalidate,
    }),
    remove: useMutation({
      mutationFn: ({ id }) => adminDeleteAccessRequest(id),
      onSuccess: invalidate,
    }),
  };
}

export default useAdminUsers;
