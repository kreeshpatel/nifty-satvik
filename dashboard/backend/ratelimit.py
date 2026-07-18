"""Shared slowapi limiter (security backlog, 2026-07-18).

One Limiter instance, keyed on the REAL client IP (netutil.client_ip — Fly's edge header in
production, so users stop sharing the proxy's single bucket). Lives in its own module so route
files can add stricter per-route limits (e.g. the public access-request form) with the same
instance main.py registers on app.state.
"""
from slowapi import Limiter

from netutil import client_ip

limiter = Limiter(key_func=client_ip, default_limits=["60/minute"])
