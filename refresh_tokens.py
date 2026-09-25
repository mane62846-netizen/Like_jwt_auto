import json
import os
import sys
import time
from pathlib import Path

import requests

UID_FILE = Path("Uid_ind.json")
TOKEN_FILE = Path("token_ind.json")


def extract_token(data):
    if isinstance(data, str) and data.strip():
        return data.strip()
    if isinstance(data, dict):
        for key in ("jwt_token", "token", "access_token", "jwt"):
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        for key in ("data", "result", "response"):
            if key in data:
                value = extract_token(data[key])
                if value:
                    return value
    if isinstance(data, list):
        for item in data:
            value = extract_token(item)
            if value:
                return value
    return None


def get_token(uid, password, session):
    url = os.environ["JWT_API_URL"].strip()
    method = os.getenv("JWT_API_METHOD", "GET").upper()
    timeout = float(os.getenv("JWT_API_TIMEOUT", "60"))

    params = {
        "uid": uid,
        "password": password,
    }
    headers = {"Accept": "application/json", "User-Agent": "OB54-Token-Refresh/1.0"}

    if method == "POST":
        response = session.post(url, json=params, headers=headers, timeout=timeout)
    else:
        response = session.get(url, params=params, headers=headers, timeout=timeout)

    response.raise_for_status()
    try:
        data = response.json()
    except ValueError:
        data = response.text

    token = extract_token(data)
    if not token:
        raise ValueError("JWT API response did not contain a token")
    return token


def main():
    if not os.getenv("JWT_API_URL"):
        print("ERROR: JWT_API_URL secret/variable is not set", file=sys.stderr)
        return 2

    if not UID_FILE.exists():
        print(f"ERROR: {UID_FILE} not found", file=sys.stderr)
        return 2

    accounts = json.loads(UID_FILE.read_text(encoding="utf-8"))
    if not isinstance(accounts, list):
        raise ValueError("Uid_ind.json must contain a JSON list")

    old_tokens = []
    if TOKEN_FILE.exists():
        try:
            old_tokens = json.loads(TOKEN_FILE.read_text(encoding="utf-8"))
        except Exception:
            old_tokens = []

    new_tokens = []
    failed = []
    session = requests.Session()

    for index, account in enumerate(accounts, 1):
        uid = str(account.get("uid", "")).strip()
        password = str(account.get("password", "")).strip()
        if not uid or not password:
            failed.append((index, uid or "<missing uid>", "missing uid/password"))
            continue

        try:
            token = get_token(uid, password, session)
            new_tokens.append({"token": token})
            print(f"[{index}/{len(accounts)}] OK {uid}")
        except Exception as exc:
            failed.append((index, uid, str(exc)))
            print(f"[{index}/{len(accounts)}] FAILED {uid}: {exc}", file=sys.stderr)

        # Small delay to avoid hammering the JWT endpoint.
        delay = float(os.getenv("JWT_API_DELAY", "0.15"))
        if delay > 0:
            time.sleep(delay)

    # Never replace a working token file with a partial refresh.
    if failed:
        print(f"Refresh failed for {len(failed)} account(s); keeping existing {TOKEN_FILE}.", file=sys.stderr)
        return 1

    tmp = TOKEN_FILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(new_tokens, ensure_ascii=False, indent=4) + "\n", encoding="utf-8")
    tmp.replace(TOKEN_FILE)
    print(f"Successfully refreshed {len(new_tokens)} tokens into {TOKEN_FILE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
