"""
logger.py — Pencatatan log kejadian keamanan ke file JSONL.

Menulis setiap aktivitas pengujian ke logs/security_events.jsonl
dalam format append-only JSON Lines (satu objek JSON per baris).

Format log per baris:
{
    "timestamp": "2026-11-20T14:30:00.123456",
    "prompt": "teks prompt (dipotong 200 karakter)",
    "confidence_score": 0.9842,
    "threshold_used": 0.65,
    "is_injection": true,
    "status": "blocked",
    "guardrail_latency_ms": 42.5,
    "total_latency_ms": 43.1
}
"""

import json
import os
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)

# Timezone WIB (UTC+7)
WIB = timezone(timedelta(hours=7))


class SecurityLogger:
    """
    Append-only JSONL logger untuk mencatat setiap transaksi keamanan.

    Setiap request ke /api/chat dicatat sebagai bukti log operasional
    yang bisa diaudit di kemudian hari.
    """

    def __init__(self):
        self._log_file = settings.log_file
        self._ensure_log_directory()

    def _ensure_log_directory(self) -> None:
        """Pastikan direktori log ada."""
        log_dir = os.path.dirname(self._log_file)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)

    def log_event(
        self,
        prompt: str,
        confidence_score: float,
        threshold_used: float,
        is_injection: bool,
        status: str,
        guardrail_latency_ms: float,
        total_latency_ms: float,
        bot_reply: Optional[str] = None,
    ) -> None:
        """
        Catat satu kejadian keamanan ke file JSONL.

        Args:
            prompt: Teks prompt asli (akan dipotong maks 200 karakter).
            confidence_score: Skor probabilitas injection dari model.
            threshold_used: Nilai threshold yang digunakan.
            is_injection: Apakah prompt terdeteksi sebagai injection.
            status: "blocked" atau "allowed".
            guardrail_latency_ms: Waktu inferensi guardrail (ms).
            total_latency_ms: Total waktu pemrosesan termasuk Ollama (ms).
            bot_reply: Balasan dari Ollama (jika ada, dipotong 200 karakter).
        """
        event = {
            "timestamp": datetime.now(WIB).isoformat(),
            "prompt": prompt[:200] + ("..." if len(prompt) > 200 else ""),
            "prompt_length": len(prompt),
            "confidence_score": confidence_score,
            "threshold_used": threshold_used,
            "is_injection": is_injection,
            "status": status,
            "guardrail_latency_ms": guardrail_latency_ms,
            "total_latency_ms": total_latency_ms,
        }

        if bot_reply is not None:
            event["bot_reply_preview"] = bot_reply[:200] + (
                "..." if len(bot_reply) > 200 else ""
            )

        try:
            with open(self._log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(event, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error(f"Gagal menulis log keamanan: {e}")


# Singleton instance
security_logger = SecurityLogger()
