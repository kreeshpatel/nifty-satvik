/**
 * Local-dev API proxy — mirrors the Vercel rewrite in production.
 *
 * In production, frontend/vercel.json rewrites /api/* → niftyquant-api.fly.dev
 * so cookies are first-party. Without an equivalent for `npm start`, local
 * dev would either:
 *   - hit a non-existent backend on localhost:3000/api/* (signals show 0,
 *     auth fails), OR
 *   - go cross-origin to Render and trip the same third-party-cookie
 *     blocking that the production proxy was added to fix.
 *
 * This proxy makes localhost:3000 behave exactly like production: /api/*
 * is same-origin to the browser, cookies are first-party, Kite OAuth and
 * signal fetch both work end-to-end.
 *
 * CRA auto-loads this file when present in src/. No imports from app code.
 */
const { createProxyMiddleware } = require('http-proxy-middleware');

const BACKEND = process.env.LOCAL_PROXY_TARGET || 'https://niftyquant-api.fly.dev';

module.exports = function (app) {
  app.use(
    '/api',
    createProxyMiddleware({
      target: BACKEND,
      changeOrigin: true,
      secure: true,
      // Forward cookies. Default behavior — explicit for clarity.
      cookieDomainRewrite: '',
      logLevel: 'warn',
    }),
  );
};
