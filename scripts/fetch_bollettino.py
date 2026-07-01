#!/usr/bin/env python3
"""Fetch the current Veneto CFD bulletin JSON and mirror it byte-identical.

Discovers the current bulletin URL from the Region's HTML page (the URL
changes on every emission/revision and embeds an unpredictable Liferay UUID),
downloads it as raw bytes, validates it as JSON, and republishes it unchanged
alongside an archival copy and a metadata sidecar.
"""

import json
import os
import re
import sys
from datetime import datetime, timezone

import requests

SOURCE_PAGE = "https://www.regione.veneto.it/web/protezione-civile/protezione-civile"
BASE_URL = "https://www.regione.veneto.it"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(REPO_ROOT, "data")
ARCHIVE_DIR = os.path.join(DATA_DIR, "archive")
BOLLETTINO_PATH = os.path.join(DATA_DIR, "bollettino.json")
META_PATH = os.path.join(DATA_DIR, "meta.json")

HREF_RE = re.compile(r'href=["\']([^"\']*BLMultiCfd[^"\']*\.json[^"\']*)["\']', re.IGNORECASE)
FILENAME_RE = re.compile(r'(BLMultiCfd[^/"\']*\.json)', re.IGNORECASE)


def log(msg):
    print(msg, flush=True)


def find_current_json_url():
    resp = requests.get(SOURCE_PAGE, headers={"User-Agent": USER_AGENT}, timeout=(10, 30))
    resp.raise_for_status()
    matches = HREF_RE.findall(resp.text)
    if not matches:
        raise RuntimeError("Nessun link BLMultiCfd*.json trovato nella pagina sorgente")
    url = matches[0]
    if url.startswith("http"):
        return url
    return BASE_URL + url


def load_previous_meta():
    if not os.path.isfile(META_PATH):
        return None
    try:
        with open(META_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def extract_filename(url):
    match = FILENAME_RE.search(url)
    if match:
        return match.group(1)
    return "bollettino.json"


def main():
    os.makedirs(ARCHIVE_DIR, exist_ok=True)

    current_url = find_current_json_url()
    log(f"URL bollettino corrente: {current_url}")

    previous_meta = load_previous_meta()
    if previous_meta and previous_meta.get("source_url") == current_url:
        log("URL invariato rispetto all'ultimo fetch: nessuna azione necessaria.")
        return 0

    resp = requests.get(current_url, headers={"User-Agent": USER_AGENT}, timeout=(10, 30))
    resp.raise_for_status()
    raw_bytes = resp.content
    log(f"Scaricati {len(raw_bytes)} byte")

    try:
        parsed = json.loads(raw_bytes)
    except json.JSONDecodeError as exc:
        log(f"Validazione JSON fallita: {exc}. File esistenti NON modificati.")
        return 1

    log("Validazione JSON: OK")

    dati_generali = parsed.get("dati_generali", {})
    filename = extract_filename(current_url)

    with open(BOLLETTINO_PATH, "wb") as f:
        f.write(raw_bytes)

    archive_path = os.path.join(ARCHIVE_DIR, filename)
    with open(archive_path, "wb") as f:
        f.write(raw_bytes)

    meta = {
        "source_url": current_url,
        "filename": filename,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "num_boll": dati_generali.get("num_boll"),
        "aggiornamento": dati_generali.get("aggiornamento"),
        "data_compilazione": dati_generali.get("data_compilazione"),
        "ora_compilazione": dati_generali.get("ora_compilazione"),
    }
    with open(META_PATH, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    log(f"Aggiornato data/bollettino.json e archiviato come {filename}")
    log("Cambiato: si")
    return 0


if __name__ == "__main__":
    sys.exit(main())
