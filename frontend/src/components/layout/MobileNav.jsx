import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { ListChecks, LayoutDashboard, LineChart, Briefcase, Trophy } from 'lucide-react';

/**
 * MobileNav — fixed bottom tab bar, shown only below 768px (see mobile.css).
 * Mirrors TopBar's PRIMARY_TABS plus Track record so the whole product is
 * reachable with a thumb. Account / settings / admin stay in the TopBar
 * avatar menu, which remains visible on mobile.
 */
const TABS = [
  { to: '/this-week',    label: 'Week',      icon: ListChecks },
  { to: '/dashboard',    label: 'Home',      icon: LayoutDashboard },
  { to: '/premove',      label: 'Research',  icon: LineChart },
  { to: '/portfolio',    label: 'Portfolio', icon: Briefcase },
  { to: '/track-record', label: 'Record',    icon: Trophy },
];

export default function MobileNav() {
  const { pathname } = useLocation();
  return (
    <nav className="mnav" aria-label="Primary">
      {TABS.map((t) => {
        const Icon = t.icon;
        const active = pathname === t.to || pathname.startsWith(t.to + '/');
        return (
          <Link
            key={t.to}
            to={t.to}
            className={`mnav-item${active ? ' on' : ''}`}
            aria-current={active ? 'page' : undefined}
          >
            <Icon size={20} strokeWidth={active ? 2.2 : 1.8} />
            <span>{t.label}</span>
          </Link>
        );
      })}
    </nav>
  );
}
