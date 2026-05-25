"""Login / logout — authenticate and store JWT."""

from __future__ import annotations


import getpass
import logging

import httpx

from .config import CLIConfig


def login(server_url: str) -> None:
    """Prompt for credentials, store JWT in config."""
    email = input("Email: ").strip()
    password = getpass.getpass("Password: ")

    resp = httpx.post(
        f"{server_url}/auth/login",
        json={"email": email, "password": password},
        timeout=15.0,
    )
    if resp.status_code != 200:
        detail = resp.json().get("detail", resp.text)
        logging.error("Login failed: %s", detail)
        raise SystemExit(1)

    token = resp.json()["access_token"]

    cfg = CLIConfig.load()
    cfg.server.url = server_url
    cfg.auth.token = token
    cfg.auth.email = email
    cfg.save()
    logging.info("Logged in as %s", email)


def logout() -> None:
    """Clear stored token."""
    cfg = CLIConfig.load()
    if cfg.auth.token:
        token = cfg.auth.token
        # Clear local state first, then notify server.
        cfg.auth.token = None
        cfg.auth.email = None
        cfg.save()
        try:
            httpx.post(
                f"{cfg.server.url}/auth/logout",
                headers={"Authorization": f"Bearer {token}"},
                timeout=5.0,
            )
        except httpx.HTTPError:
            logging.warning(
                "Logged out locally — server logout failed (network error)"
            )
            return
    else:
        cfg.save()
    logging.info("Logged out")
