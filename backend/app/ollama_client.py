"""
ollama_client.py — Klien HTTP asinkron untuk komunikasi ke container Ollama.

Menggunakan httpx.AsyncClient dengan timeout yang dikonfigurasi.
Berkomunikasi melalui jaringan internal Docker (guardrail_net).
"""

import logging
from typing import Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class OllamaClient:
    """
    Async HTTP client untuk berkomunikasi dengan Ollama service.

    Mengirim prompt ke endpoint /api/chat Ollama dan mengembalikan
    respons dari model LLM.
    """

    def __init__(self):
        self._client: Optional[httpx.AsyncClient] = None

    async def initialize(self) -> None:
        """Inisialisasi HTTP client. Dipanggil saat startup FastAPI."""
        self._client = httpx.AsyncClient(
            base_url=settings.ollama_base_url,
            timeout=httpx.Timeout(
                connect=10.0,
                read=float(settings.ollama_timeout),
                write=10.0,
                pool=10.0,
            ),
        )
        logger.info(
            f"✅ Ollama client diinisialisasi — "
            f"URL: {settings.ollama_base_url}, "
            f"Model: {settings.ollama_model}"
        )

    async def close(self) -> None:
        """Tutup HTTP client. Dipanggil saat shutdown FastAPI."""
        if self._client:
            await self._client.aclose()
            logger.info("Ollama client ditutup.")

    async def chat(self, user_prompt: str) -> str:
        """
        Kirim prompt pengguna ke Ollama dan kembalikan teks respons.

        Args:
            user_prompt: Teks prompt dari pengguna yang sudah lolos guardrail.

        Returns:
            Teks balasan dari model LLM Ollama.

        Raises:
            ConnectionError: Jika Ollama service tidak dapat dijangkau.
            TimeoutError: Jika request melebihi batas timeout.
        """
        if not self._client:
            raise RuntimeError("Ollama client belum diinisialisasi.")

        payload = {
            "model": settings.ollama_model,
            "messages": [
                {
                    "role": "system",
                    "content": settings.system_prompt,
                },
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ],
            "stream": False,
        }

        try:
            response = await self._client.post("/api/chat", json=payload)
            response.raise_for_status()

            data = response.json()

            # Ekstrak teks balasan dari respons Ollama
            bot_reply = (
                data.get("message", {}).get("content", "")
                or data.get("response", "")
            )

            return bot_reply.strip()

        except httpx.ConnectError:
            error_msg = (
                f"Tidak dapat terhubung ke Ollama di {settings.ollama_base_url}. "
                "Pastikan container ollama-service sudah berjalan."
            )
            logger.error(error_msg)
            raise ConnectionError(error_msg)

        except httpx.TimeoutException:
            error_msg = (
                f"Request ke Ollama timeout setelah {settings.ollama_timeout} detik. "
                "Model mungkin sedang loading atau prompt terlalu kompleks."
            )
            logger.error(error_msg)
            raise TimeoutError(error_msg)

        except httpx.HTTPStatusError as e:
            error_msg = f"Ollama mengembalikan error HTTP {e.response.status_code}: {e.response.text}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

    async def health_check(self) -> bool:
        """
        Periksa apakah Ollama service bisa dijangkau.

        Returns:
            True jika Ollama merespons, False jika tidak.
        """
        if not self._client:
            return False

        try:
            response = await self._client.get("/api/tags")
            return response.status_code == 200
        except Exception:
            return False


# Singleton instance — diinisialisasi oleh FastAPI lifespan
ollama_client = OllamaClient()
