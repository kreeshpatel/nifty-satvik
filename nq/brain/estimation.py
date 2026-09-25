"""How much of a small sample covariance is signal, and what a weighting scheme could do with it.

Track P2 of the Satvik Brain plan. The question these functions exist to answer is not "what are the
optimal weights" — it is **whether the weighting axis is resolvable at all** on a book of about five
names that rotate weekly. Two independent instruments say how much of an estimated covariance is
noise:

* **Marchenko-Pastur.** The eigenvalues of a correlation matrix estimated from `T` observations of
  `N` pure-noise series fill a known band. Sample eigenvalues inside that band are what noise alone
  produces, so they carry no usable information about co-movement.
* **Ledoit-Wolf.** The optimal shrinkage intensity toward the constant-correlation target says how
  adequate a single average correlation is as a summary of the whole matrix.

  **It is not a noise statistic, and it must not be read as one.** delta* = (pi - rho)/(gamma*T), and
  gamma is the squared distance from the sample matrix to that target. When every pairwise correlation
  is alike, the target is nearly perfect and delta* approaches 1 *at any sample size* — on iid noise
  it is ~0.99 even at T = 2000, where estimation error is negligible. Track P2 first read a delta* of
  0.98 as "98% of this covariance is noise"; that inference is wrong and
  `tests/test_brain_estimation.py::test_shrinkage_intensity_is_not_a_noise_statistic` now pins it.
  What a high delta* does say is that there is little DIFFERENTIAL correlation structure to exploit,
  which is a claim about what an optimiser could do, not about sample length.

The optimisers are long-only, fully invested and capped, because that is the book being described —
it is cash-constrained and cannot short or lever. Exposure changes are 0095's question (killed on
this book at ΔSharpe −0.398) and deliberately not askable here: every weight vector returned sums to
one, so the caller re-splits the same money and changes nothing else.
"""

from __future__ import annotations

import numpy as np
import numpy.typing as npt
from scipy.optimize import minimize

Floats = npt.NDArray[np.float64]

TRADING_DAYS = 252
# The programme's resolution floor: n_eff = 37 independent 63-day windows on 2017-2026 Indian daily
# equity data (diagnostics/research/n_trials.json). No edge below this is resolvable at any trial
# count. Imported rather than retyped wherever a bound is read.
DSHARPE_HALF_WIDTH = 0.59


# --------------------------------------------------------------------------- how much is noise
def marchenko_pastur_edges(q: float) -> tuple[float, float]:
    """Bulk edges `(1 ∓ √q)²` for a correlation matrix of `N = qT` pure-noise series.

    Unit variance, so σ² = 1 and the edges depend only on the shape ratio.
    """
    if not 0 < q:
        raise ValueError(f"q must be positive, got {q}")
    root = np.sqrt(q)
    return float((1 - root) ** 2), float((1 + root) ** 2)


def mp_noise_share(corr: Floats, q: float) -> float:
    """Share of a correlation matrix's eigenvalues that lie inside the pure-noise bulk.

    1.0 means every mode of co-movement in this matrix is one that `N` unrelated series would have
    produced anyway from `T` observations.
    """
    lo, hi = marchenko_pastur_edges(q)
    eig = np.linalg.eigvalsh(np.asarray(corr, dtype=float))
    return float(np.mean((eig >= lo) & (eig <= hi)))


def ledoit_wolf_shrinkage(returns: Floats) -> tuple[float, Floats]:
    """Optimal shrinkage intensity `δ*` toward the constant-correlation target, and the shrunk matrix.

    Ledoit & Wolf (2004), "Honey, I Shrunk the Sample Covariance Matrix". `δ*` is clipped to [0, 1]
    as the paper prescribes; δ* near 1 says the sample matrix carries almost nothing the average
    correlation does not already say — see the module docstring for what that does and does not mean,
    because the clip also means δ* saturates and differences near 1 are not informative.
    """
    x = np.asarray(returns, dtype=float)
    t, n = x.shape
    if t < 2 or n < 2:
        raise ValueError(f"need at least 2 observations and 2 series, got {x.shape}")
    x = x - x.mean(axis=0)
    s = (x.T @ x) / t
    var = np.diag(s).copy()
    sd = np.sqrt(var)
    outer_sd = np.outer(sd, sd)
    with np.errstate(divide="ignore", invalid="ignore"):
        corr = np.where(outer_sd > 0, s / outer_sd, 0.0)
    off = ~np.eye(n, dtype=bool)
    r_bar = float(corr[off].mean())

    target = r_bar * outer_sd
    np.fill_diagonal(target, var)

    # pi: variance of each sample covariance entry
    x2 = x ** 2
    pi_mat = (x2.T @ x2) / t - 2 * s * ((x.T @ x) / t) + s ** 2
    pi_hat = float(pi_mat.sum())

    # rho: covariance between the sample entries and the estimated parts of the target.
    # theta_ii,ij = E[(x_i^2 - s_ii)(x_i x_j - s_ij)] = E[x_i^3 x_j] - s_ii s_ij — note the CUBE: the
    # first factor multiplies the product x_i x_j, not x_j alone.
    theta_ii = ((x2 * x).T @ x) / t - var[:, None] * s
    theta_jj = theta_ii.T
    with np.errstate(divide="ignore", invalid="ignore"):
        safe_var = np.where(var > 0, var, np.nan)
        ratio = np.sqrt(np.outer(var, 1.0 / safe_var))          # ratio_ij = sqrt(var_i / var_j)
    # the paper pairs sqrt(s_jj/s_ii) with theta_ii and sqrt(s_ii/s_jj) with theta_jj
    cross = np.nan_to_num((r_bar / 2.0) * (theta_ii / ratio + theta_jj * ratio))
    rho_hat = float(np.diag(pi_mat).sum() + cross[off].sum())

    gamma_hat = float(((target - s) ** 2).sum())
    if gamma_hat <= 0:
        return 0.0, s
    delta = (pi_hat - rho_hat) / gamma_hat / t
    delta = float(min(1.0, max(0.0, delta)))
    return delta, delta * target + (1 - delta) * s


def joint_holding_sessions(held_by_day: dict, names: tuple[str, str]) -> int:
    """Sessions on which both names were actually held.

    A correlation estimated over 63 sessions that governs a 15-session shared holding is mostly
    describing a period in which neither position existed.
    """
    a, b = names
    return sum(1 for d in held_by_day if a in held_by_day[d] and b in held_by_day[d])


# --------------------------------------------------------------------------- weighting schemes
def _clean(w: Floats) -> Floats:
    w = np.clip(np.asarray(w, dtype=float), 0.0, None)
    total = w.sum()
    return w / total if total > 0 else np.full(len(w), 1.0 / len(w))


def equal_weights(n: int) -> Floats:
    return np.full(n, 1.0 / n)


def inverse_vol_weights(vols: Floats, cap: float = 1.0) -> Floats:
    v = np.asarray(vols, dtype=float)
    w = np.where(v > 0, 1.0 / np.where(v > 0, v, np.nan), 0.0)
    return _apply_cap(_clean(np.nan_to_num(w)), cap)


def _apply_cap(w: Floats, cap: float) -> Floats:
    """Water-fill the excess above `cap` onto the uncapped names, repeatedly until it settles."""
    w = _clean(w)
    if cap >= 1.0:
        return w
    for _ in range(len(w) + 1):
        over = w > cap + 1e-12
        if not over.any():
            return w
        excess = float((w[over] - cap).sum())
        w = np.where(over, cap, w)
        room = ~over
        if not room.any():
            return np.full(len(w), 1.0 / len(w))
        w = w + room * excess * (w * room) / max(float((w * room).sum()), 1e-12)
    return _clean(w)


def _solve(objective, n: int, cap: float) -> Floats:
    """Long-only, fully invested, capped. Two starts, because SLSQP finds a local optimum."""
    cap = max(cap, 1.0 / n)                       # a cap below 1/n cannot be met by any feasible w
    cons = ({"type": "eq", "fun": lambda w: w.sum() - 1.0},)
    bounds = [(0.0, cap)] * n
    best, best_val = equal_weights(n), np.inf
    starts = [equal_weights(n)]
    for start in starts:
        res = minimize(objective, start, method="SLSQP", bounds=bounds, constraints=cons,
                       options={"maxiter": 200, "ftol": 1e-10})
        if res.success and res.fun < best_val:
            best, best_val = _apply_cap(_clean(res.x), cap), float(res.fun)
    return best


def min_variance_weights(cov: Floats, cap: float = 1.0) -> Floats:
    c = np.asarray(cov, dtype=float)
    return _solve(lambda w: float(w @ c @ w), c.shape[0], cap)


def max_sharpe_weights(mu: Floats, cov: Floats, cap: float = 1.0) -> Floats:
    """Long-only max `w'μ / √(w'Σw)`.

    With every `μ` negative the ratio is still well defined and the optimiser picks the least-bad
    risk-adjusted mix, which is the honest answer for a long-only book that cannot step aside — the
    cash decision is a different axis and is not this one.
    """
    m = np.asarray(mu, dtype=float)
    c = np.asarray(cov, dtype=float)

    def neg_sharpe(w: Floats) -> float:
        vol = float(np.sqrt(max(w @ c @ w, 1e-18)))
        return -float(w @ m) / vol

    return _solve(neg_sharpe, len(m), cap)


def max_return_weights(mu: Floats, cap: float = 1.0) -> Floats:
    """The pure return ceiling: everything on the best name, capped. No optimiser needed."""
    m = np.asarray(mu, dtype=float)
    order = np.argsort(-m)
    w = np.zeros(len(m))
    cap = max(cap, 1.0 / len(m))
    left = 1.0
    for i in order:
        take = min(cap, left)
        w[i] = take
        left -= take
        if left <= 1e-12:
            break
    return _clean(w)


# --------------------------------------------------------------------------- reading the result
def sharpe(daily: Floats, periods: int = TRADING_DAYS) -> float:
    r = np.asarray(daily, dtype=float)
    r = r[np.isfinite(r)]
    sd = r.std(ddof=1)
    if len(r) < 2 or sd == 0:
        return float("nan")
    return float(r.mean() / sd * np.sqrt(periods))


def resolvable(delta_sharpe: float, half_width: float = DSHARPE_HALF_WIDTH) -> bool:
    """Is a ΔSharpe big enough for this data to see it at all? Sign-blind, as the floor is."""
    return bool(abs(float(delta_sharpe)) >= half_width)
