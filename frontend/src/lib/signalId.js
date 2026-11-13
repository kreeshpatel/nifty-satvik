/**
 * The id that joins a model signal to a user's recorded fills. The signals API does not send a
 * `signal_id`; it is derived as `${TICKER}__${signal_date}` (same rule as ThisWeek / SignalsV3,
 * and the backend execution ledger keys fills by it).
 */
export const signalIdOf = (s) => {
  const t = String(s?.ticker || s?.sym || '').toUpperCase();
  return s?.signal_id || (t && s?.signal_date ? `${t}__${s.signal_date}` : null);
};
