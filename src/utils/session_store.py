"""
Simpan / muat sesi paste + histori perbandingan.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from config.settings import BASE_DIR

SESSIONS_DIR = BASE_DIR / "data" / "sessions"
HISTORY_FILE = BASE_DIR / "data" / "history" / "history.json"

SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)


def save_session(
    product_code: str,
    product_name: str,
    raw_sistem: str,
    raw_masuk: str,
    raw_keluar: str,
    label: Optional[str] = None,
    summary: Optional[Dict[str, Any]] = None,
) -> Path:
    """Simpan sesi ke file JSON. Return path file."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    code = (product_code or "produk").replace(" ", "_")[:20]
    name = label or f"{code}_{ts}"
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in name)
    path = SESSIONS_DIR / f"{safe}.json"

    payload = {
        "saved_at": datetime.now().isoformat(timespec="seconds"),
        "label": name,
        "product_code": product_code,
        "product_name": product_name,
        "raw_sistem": raw_sistem or "",
        "raw_masuk": raw_masuk or "",
        "raw_keluar": raw_keluar or "",
        "summary": summary or {},
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    _append_history(path, payload)
    return path


def load_session(path: Path) -> Dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data


def list_sessions(limit: int = 30) -> List[Dict[str, Any]]:
    files = sorted(SESSIONS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    out = []
    for f in files[:limit]:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            out.append({
                "path": str(f),
                "name": f.name,
                "label": data.get("label") or f.stem,
                "saved_at": data.get("saved_at", ""),
                "product_code": data.get("product_code", ""),
                "product_name": data.get("product_name", ""),
                "selisih_netto": (data.get("summary") or {}).get("selisih_netto"),
            })
        except Exception:
            continue
    return out


def delete_session(path: Path) -> bool:
    try:
        path.unlink(missing_ok=True)
        return True
    except Exception:
        return False


def _append_history(path: Path, payload: Dict[str, Any]) -> None:
    history = _read_history()
    history.insert(0, {
        "saved_at": payload.get("saved_at"),
        "label": payload.get("label"),
        "product_code": payload.get("product_code"),
        "product_name": payload.get("product_name"),
        "selisih_netto": (payload.get("summary") or {}).get("selisih_netto"),
        "session_file": path.name,
    })
    history = history[:50]
    HISTORY_FILE.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")


def _read_history() -> List[Dict[str, Any]]:
    if not HISTORY_FILE.exists():
        return []
    try:
        return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def get_history(limit: int = 20) -> List[Dict[str, Any]]:
    return _read_history()[:limit]
