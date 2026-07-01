import React from 'react';
import '../styles/liquid-glass.css';

/**
 * Apple Liquid Glass Example Component
 * Demonstrates the iOS 26 / macOS Sequoia design language
 */
export default function LiquidGlassExample() {
  return (
    <>
      {/* Background Scene */}
      <div className="liquid-glass-bg">
        <div className="orb-1" />
        <div className="orb-2" />
      </div>
      <div className="grain-overlay" />

      {/* Main Content */}
      <div className="relative z-1" style={{ padding: '24px 32px', minHeight: '100vh' }}>
        {/* Navigation Bar - z-4 */}
        <nav className="glass-regular z-4 spring-appear" style={{ 
          borderRadius: 'var(--radius-2xl)',
          padding: 'var(--space-4)',
          marginBottom: 'var(--space-6)',
        }}>
          <div className="flex items-center justify-between">
            <h1 className="text-title1" style={{ color: 'var(--text-primary)' }}>
              NiftyQuant
            </h1>
            <div className="flex items-center gap-3">
              <button className="btn-secondary">
                Portfolio
              </button>
              <button className="btn-primary">
                New Trade
              </button>
            </div>
          </div>
        </nav>

        {/* Hero Section */}
        <div className="mb-8">
          <h2 className="text-large-title mb-2">
            Portfolio Performance
          </h2>
          <p className="text-subheadline" style={{ color: 'var(--text-secondary)' }}>
            Track your investments in real-time
          </p>
        </div>

        {/* Card Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
          {/* Card 1 - Total Value */}
          <div className="glass-regular liquid-card spring-slide z-2" style={{ padding: 'var(--space-6)' }}>
            <div className="flex items-center justify-between mb-4">
              <span className="text-callout" style={{ color: 'var(--text-tertiary)' }}>
                Total Value
              </span>
              <div className="w-10 h-10 rounded-full flex items-center justify-center" style={{ background: 'rgba(10, 132, 255, 0.15)' }}>
                <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                  <path d="M10 2L2 7L10 12L18 7L10 2Z" fill="var(--apple-blue)" />
                </svg>
              </div>
            </div>
            <h3 className="text-title1 mb-1" style={{ color: 'var(--text-primary)' }}>
              ₹50,12,450
            </h3>
            <div className="flex items-center gap-2">
              <span className="text-footnote" style={{ 
                color: 'var(--apple-green)',
                background: 'rgba(48, 209, 88, 0.15)',
                padding: '4px 8px',
                borderRadius: 'var(--radius-sm)',
              }}>
                +2.4%
              </span>
              <span className="text-footnote" style={{ color: 'var(--text-tertiary)' }}>
                +₹12,450 today
              </span>
            </div>
          </div>

          {/* Card 2 - Active Positions */}
          <div className="glass-regular liquid-card spring-slide z-2" style={{ 
            padding: 'var(--space-6)',
            animationDelay: '50ms',
          }}>
            <div className="flex items-center justify-between mb-4">
              <span className="text-callout" style={{ color: 'var(--text-tertiary)' }}>
                Active Positions
              </span>
              <div className="w-10 h-10 rounded-full flex items-center justify-center" style={{ background: 'rgba(191, 90, 242, 0.15)' }}>
                <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                  <circle cx="10" cy="10" r="8" fill="var(--apple-purple)" />
                </svg>
              </div>
            </div>
            <h3 className="text-title1 mb-1" style={{ color: 'var(--text-primary)' }}>
              12
            </h3>
            <div className="flex items-center gap-2">
              <span className="text-footnote" style={{ color: 'var(--text-tertiary)' }}>
                8 profitable · 4 loss
              </span>
            </div>
          </div>

          {/* Card 3 - Signals */}
          <div className="glass-regular liquid-card spring-slide z-2" style={{ 
            padding: 'var(--space-6)',
            animationDelay: '100ms',
          }}>
            <div className="flex items-center justify-between mb-4">
              <span className="text-callout" style={{ color: 'var(--text-tertiary)' }}>
                Pre-Move Signals
              </span>
              <div className="w-10 h-10 rounded-full flex items-center justify-center" style={{ background: 'rgba(255, 159, 10, 0.15)' }}>
                <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                  <path d="M10 2L12 8L18 10L12 12L10 18L8 12L2 10L8 8L10 2Z" fill="var(--apple-orange)" />
                </svg>
              </div>
            </div>
            <h3 className="text-title1 mb-1" style={{ color: 'var(--text-primary)' }}>
              5
            </h3>
            <div className="flex items-center gap-2">
              <span className="text-footnote" style={{ color: 'var(--text-tertiary)' }}>
                3 high confidence
              </span>
            </div>
          </div>
        </div>

        {/* List with Glass Rows */}
        <div className="glass-regular liquid-card z-2" style={{ padding: 0, overflow: 'hidden' }}>
          <div style={{ padding: 'var(--space-6)' }}>
            <h3 className="text-headline" style={{ color: 'var(--text-primary)' }}>
              Top Holdings
            </h3>
          </div>

          {/* List Items */}
          {[
            { symbol: 'RELIANCE', name: 'Reliance Industries', value: '₹73,554', change: '+1.8%', isPositive: true },
            { symbol: 'TCS', name: 'Tata Consultancy Services', value: '₹58,386', change: '+2.1%', isPositive: true },
            { symbol: 'HDFCBANK', name: 'HDFC Bank', value: '₹58,080', change: '-1.2%', isPositive: false },
            { symbol: 'INFY', name: 'Infosys', value: '₹81,077', change: '-0.5%', isPositive: false },
          ].map((stock, idx) => (
            <div
              key={idx}
              className="glass-ultra-thin"
              style={{
                padding: 'var(--space-4) var(--space-6)',
                borderTop: idx === 0 ? 'none' : '1px solid rgba(255, 255, 255, 0.1)',
                minHeight: '44px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                cursor: 'pointer',
                transition: 'all 150ms ease-out',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = 'rgba(255, 255, 255, 0.12)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = 'var(--glass-ultra-thin)';
              }}
            >
              <div>
                <div className="text-body" style={{ color: 'var(--text-primary)' }}>
                  {stock.symbol}
                </div>
                <div className="text-footnote" style={{ color: 'var(--text-tertiary)' }}>
                  {stock.name}
                </div>
              </div>
              <div className="text-right">
                <div className="text-body" style={{ color: 'var(--text-primary)' }}>
                  {stock.value}
                </div>
                <div
                  className="text-footnote"
                  style={{
                    color: stock.isPositive ? 'var(--apple-green)' : 'var(--apple-red)',
                  }}
                >
                  {stock.change}
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Action Buttons */}
        <div className="mt-8 flex gap-4">
          <button className="btn-primary focus-ring">
            View All Positions
          </button>
          <button className="btn-secondary focus-ring">
            Add to Watchlist
          </button>
          <button className="btn-destructive focus-ring">
            Sell All
          </button>
        </div>
      </div>
    </>
  );
}
