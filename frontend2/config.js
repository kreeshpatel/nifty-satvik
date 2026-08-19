/* Parallel frontend config. Point apiBase at the live backend.
   - Same-origin deploy (backend serves this folder): leave "/api".
   - Separate Vercel/static deploy: set the full backend origin, e.g.
       apiBase: "https://nifty-satvik-api.fly.dev/api"
     and ensure the backend CORS allows this origin with credentials.
   The app falls back to bundled sample data whenever a call fails or returns
   nothing (e.g. not logged in), so it always renders. The top-right badge shows
   LIVE vs SAMPLE. */
window.NQ_CONFIG = {
  apiBase: "/api",
  navHistoryDays: 365,
  candleInterval: "1wk",
  candlePeriod: "2y",
};
