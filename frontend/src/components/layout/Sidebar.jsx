import React, { useContext, useState } from 'react';
import { cn } from '@/lib/utils';
import { useLocation, useNavigate } from 'react-router-dom';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  LayoutDashboard, Zap, Briefcase, ListOrdered, Wallet, BarChart3, BookOpen,
  Trophy, FlaskConical, Receipt, Settings as SettingsIcon,
  ChevronLeft, ChevronRight, User, Crown, Shield, LogOut, Menu,
} from 'lucide-react';
import { AuthContext } from '@/context/AuthContext';

const iconMap = {
  LayoutDashboard, Zap, Briefcase, ListOrdered, Wallet, BarChart3, BookOpen,
  Trophy, FlaskConical, Receipt, SettingsIcon, Shield,
};

// Trading-first order: frequency of use descending
const navItems = [
  { label: 'Dashboard', icon: 'LayoutDashboard', path: '/dashboard' },
  { label: 'Signals', icon: 'Zap', path: '/premove' },
  { label: 'Portfolio', icon: 'Briefcase', path: '/portfolio' },
  { label: 'Orders', icon: 'ListOrdered', path: '/orders' },
  { label: 'Funds', icon: 'Wallet', path: '/funds' },
  { label: 'Analytics', icon: 'BarChart3', path: '/pnl' },
  { label: 'Journal', icon: 'BookOpen', path: '/journal' },
  { label: 'Track Record', icon: 'Trophy', path: '/track-record' },
  { label: 'Backtest', icon: 'FlaskConical', path: '/backtest' },
  { label: 'Accounting', icon: 'Receipt', path: '/accounting' },
  { label: 'Settings', icon: 'SettingsIcon', path: '/settings' },
];

/* ─── Mobile bottom navigation bar ─── */
const MobileBottomNav = ({ items, isActive, onNavigate }) => (
  <nav
    className="fixed bottom-0 left-0 right-0 z-50 flex md:hidden items-center justify-around"
    style={{
      height: 64,
      background: 'rgba(10,14,34,0.55)',
      backdropFilter: 'blur(28px) saturate(160%)',
      WebkitBackdropFilter: 'blur(28px) saturate(160%)',
      borderTop: '1px solid var(--edge-1)',
      paddingBottom: 'env(safe-area-inset-bottom, 0px)',
    }}
  >
    {items.slice(0, 5).map((item) => {
      const Icon = iconMap[item.icon];
      const active = isActive(item);
      return (
        <button
          key={item.label}
          onClick={() => onNavigate(item.path)}
          className="flex flex-col items-center justify-center gap-0.5 flex-1 py-2"
          style={{ color: active ? 'var(--brand)' : 'var(--text-3)' }}
        >
          <Icon className="h-5 w-5" />
          <span className="text-[10px] font-medium leading-none">{item.label}</span>
        </button>
      );
    })}
    {/* More button for overflow items */}
    {items.length > 5 && (
      <MobileMoreMenu items={items.slice(5)} isActive={isActive} onNavigate={onNavigate} />
    )}
  </nav>
);

/* ─── "More" dropdown for extra nav items on mobile ─── */
const MobileMoreMenu = ({ items, isActive, onNavigate }) => {
  const [open, setOpen] = useState(false);
  return (
    <div className="relative flex flex-col items-center justify-center gap-0.5 flex-1 py-2">
      <button
        onClick={() => setOpen(!open)}
        className="flex flex-col items-center justify-center gap-0.5"
        style={{ color: open ? 'var(--brand)' : 'var(--text-3)' }}
      >
        <Menu className="h-5 w-5" />
        <span className="text-[10px] font-medium leading-none">More</span>
      </button>
      {open && (
        <>
          {/* Backdrop */}
          <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
          {/* Menu */}
          <div
            className="absolute bottom-full right-0 mb-2 z-50 py-1 min-w-[160px] rounded-xl"
            style={{
              background: 'var(--surface-1)',
              border: '1px solid var(--edge-1)',
              boxShadow: 'var(--shadow-lg)',
            }}
          >
            {items.map((item) => {
              const Icon = iconMap[item.icon];
              const active = isActive(item);
              return (
                <button
                  key={item.label}
                  onClick={() => { onNavigate(item.path); setOpen(false); }}
                  className="flex items-center gap-3 w-full px-4 py-3 text-sm font-medium transition-colors"
                  style={{ color: active ? 'var(--brand)' : 'var(--text-2)' }}
                >
                  <Icon className="h-4 w-4" />
                  {item.label}
                </button>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
};

/* ─── Desktop sidebar (hidden on mobile) ─── */
export const Sidebar = ({ collapsed, onToggle }) => {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useContext(AuthContext);

  const allNavItems = user?.is_admin
    ? [...navItems, { label: 'Admin', icon: 'Shield', path: '/admin' }]
    : navItems;

  const isActive = (item) => {
    return location.pathname === item.path || location.pathname.startsWith(item.path + '/');
  };

  return (
    <>
      {/* ─── Desktop Sidebar ─── */}
      <aside
        className={cn(
          'fixed left-0 top-0 h-screen z-40 hidden md:flex flex-col',
          'transition-[width] duration-300 ease-in-out',
          collapsed ? 'w-[72px]' : 'w-[240px]'
        )}
        style={{
          background: 'rgba(10,14,34,0.55)',
          backdropFilter: 'blur(28px) saturate(160%)',
          WebkitBackdropFilter: 'blur(28px) saturate(160%)',
          borderRight: '1px solid var(--edge-1)',
        }}
      >
        {/* Logo */}
        <div className="flex items-center gap-3" style={{ padding: '20px 16px' }}>
          <div
            className="flex h-9 w-9 items-center justify-center shrink-0 cursor-pointer"
            style={{
              background: 'var(--brand-grad)',
              borderRadius: 'var(--r-chip)',
            }}
            onClick={() => navigate('/dashboard')}
          >
            <BarChart3 className="h-5 w-5" style={{ color: '#ffffff' }} />
          </div>
          {!collapsed && (
            <span
              className="text-base font-semibold font-heading tracking-tight cursor-pointer text-white"
              onClick={() => navigate('/dashboard')}
            >
              NiftyQuant
            </span>
          )}
        </div>

        <div className="mx-4" style={{ height: 1, background: 'var(--edge-1)' }} />

        <ScrollArea className="flex-1 px-2 py-3">
          <nav className="flex flex-col gap-1">
            {allNavItems.map((item) => {
              const Icon = iconMap[item.icon];
              const active = isActive(item);
              return (
                <button
                  key={item.label}
                  onClick={() => navigate(item.path)}
                  className={cn(
                    'flex items-center gap-3 rounded-xl px-3 text-sm font-medium transition-all duration-200 relative',
                    collapsed && 'justify-center'
                  )}
                  style={{
                    height: 40,
                    color: active ? 'var(--text-1)' : 'var(--text-3)',
                    background: active ? 'var(--brand-soft)' : 'transparent',
                    boxShadow: active
                      ? 'inset 0 0 0 1px var(--brand-edge)'
                      : 'none',
                  }}
                  onMouseEnter={(e) => {
                    if (!active) {
                      e.currentTarget.style.background = 'var(--surface-2)';
                      e.currentTarget.style.color = 'var(--text-2)';
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (!active) {
                      e.currentTarget.style.background = 'transparent';
                      e.currentTarget.style.color = 'var(--text-3)';
                    }
                  }}
                >
                  {active && (
                    <div
                      className="absolute left-0 top-1/2 -translate-y-1/2 w-[2px] rounded-r-full"
                      style={{
                        height: 20,
                        background: 'var(--brand)',
                      }}
                    />
                  )}
                  <Icon className="h-5 w-5 shrink-0" style={{ color: active ? 'var(--brand)' : undefined }} />
                  {!collapsed && <span>{item.label}</span>}
                </button>
              );
            })}
          </nav>
        </ScrollArea>

        <div className="px-2 py-2">
          <button
            onClick={onToggle}
            className="flex w-full items-center justify-center rounded-xl transition-all duration-200"
            style={{ height: 32, color: '#6B7280' }}
            onMouseEnter={(e) => { e.currentTarget.style.background = 'rgba(255,255,255,0.04)'; e.currentTarget.style.color = '#D1D5DB'; }}
            onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = '#6B7280'; }}
          >
            {collapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
          </button>
        </div>

        <div className="mx-4" style={{ height: 1, background: 'linear-gradient(90deg, transparent, rgba(255,255,255,0.06), transparent)' }} />

        <div className={cn('py-3', collapsed ? 'px-2' : 'px-3')}>
          <div className={cn('flex items-center gap-3', collapsed && 'justify-center')}>
            <div className="relative">
              <div
                className="flex h-9 w-9 items-center justify-center rounded-full cursor-pointer"
                style={{
                  background: 'var(--brand-soft)',
                  border: '1px solid var(--brand-edge)',
                }}
                onClick={() => navigate('/settings')}
                title="Settings"
              >
                <User className="h-4 w-4" style={{ color: '#ffffff' }} />
              </div>
              <div
                className="absolute -bottom-0.5 -right-0.5 h-3 w-3 rounded-full"
                style={{ background: 'var(--bull)', border: '2px solid #000000' }}
              />
            </div>
            {!collapsed && (
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate text-white">{user?.name || 'User'}</p>
                <div className="flex items-center gap-1.5">
                  {user?.is_admin ? (
                    <>
                      <Shield className="h-3 w-3" style={{ color: 'var(--brand)' }} />
                      <span className="text-[10px] font-mono tracking-wide" style={{ color: '#6B7280' }}>Admin</span>
                    </>
                  ) : (
                    <>
                      <Crown className="h-3 w-3" style={{ color: 'var(--brand)' }} />
                      <span className="text-[10px] font-mono tracking-wide" style={{ color: '#6B7280' }}>Member</span>
                    </>
                  )}
                </div>
              </div>
            )}
            {!collapsed && (
              <button
                onClick={logout}
                className="flex h-7 w-7 items-center justify-center rounded-lg transition-colors"
                style={{ color: '#6B7280' }}
                onMouseEnter={(e) => { e.currentTarget.style.color = '#ef4444'; e.currentTarget.style.background = 'rgba(239,68,68,0.1)'; }}
                onMouseLeave={(e) => { e.currentTarget.style.color = '#6B7280'; e.currentTarget.style.background = 'transparent'; }}
                title="Logout"
              >
                <LogOut className="h-3.5 w-3.5" />
              </button>
            )}
          </div>
        </div>
      </aside>

      {/* ─── Mobile Bottom Nav ─── */}
      <MobileBottomNav items={allNavItems} isActive={isActive} onNavigate={navigate} />
    </>
  );
};
