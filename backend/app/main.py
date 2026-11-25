"""
main.py — Entry point FastAPI, routing endpoint /api/chat & penyaji Web UI.

Mengatur:
- Lifespan events (startup/shutdown) untuk singleton model loading
- Route API: POST /api/chat, GET /api/health
- Static files mount untuk Web Chat UI
"""

import time
import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.config import settings
from app.detector import detector
from app.ollama_client import ollama_client
from app.logger import security_logger

# Konfigurasi logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("guardrail")


# ============================================================
# Lifespan — Singleton Model Loading (startup) & Cleanup (shutdown)
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Muat model ONNX dan inisialisasi Ollama client SATU KALI saat startup.
    Bersihkan resource saat shutdown.
    """
    # --- STARTUP ---
    log.info("=" * 60)
    log.info("🚀 Memulai Prompt Injection Guardrail Service...")
    log.info("=" * 60)

    # Muat model guardrail (ONNX atau mock)
    detector.load_model(settings.model_path)
    log.info(
        f"   Model Path  : {settings.model_path}"
        f" ({'MOCK' if detector.is_mock else 'ONNX'})"
    )
    log.info(f"   Threshold   : {settings.default_threshold}")

    # Inisialisasi Ollama client
    await ollama_client.initialize()
    log.info(f"   Ollama URL  : {settings.ollama_base_url}")
    log.info(f"   Ollama Model: {settings.ollama_model}")

    log.info("=" * 60)
    log.info("✅ Guardrail Service siap menerima request!")
    log.info("=" * 60)

    yield  # Aplikasi berjalan di sini

    # --- SHUTDOWN ---
    log.info("🛑 Mematikan Guardrail Service...")
    await ollama_client.close()
    log.info("Service berhasil dimatikan.")


# ============================================================
# FastAPI App Instance
# ============================================================

app = FastAPI(
    title="Prompt Injection Guardrail",
    description=(
        "Sistem middleware deteksi serangan prompt injection "
        "untuk perlindungan aplikasi chatbot berbasis LLM."
    ),
    version="1.0.0",
    lifespan=lifespan,
)


# ============================================================
# Request & Response Models (Pydantic)
# ============================================================

class ChatRequest(BaseModel):
    """Request body untuk POST /api/chat."""
    prompt: str = Field(
        ...,
        min_length=1,
        description="Teks prompt dari pengguna (minimal 1 karakter)"
    )
    threshold: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Override threshold deteksi (opsional)"
    )


class ChatResponse(BaseModel):
    """Response body untuk POST /api/chat."""
    status: str                            # "allowed" atau "blocked"
    is_injection: bool                     # True jika terdeteksi injection
    confidence_score: float                # Probabilitas kelas injection
    threshold_used: float                  # Threshold yang digunakan
    guardrail_latency_ms: float            # Waktu inferensi guardrail (ms)
    total_latency_ms: float                # Total waktu pemrosesan (ms)
    message: str                           # Pesan penjelasan keputusan
    bot_reply: Optional[str] = None        # Balasan dari Ollama (null jika diblokir)


class HealthResponse(BaseModel):
    """Response body untuk GET /api/health."""
    status: str
    model_loaded: bool
    model_mode: str
    ollama_connected: bool
    threshold: float
    ollama_model: str


# ============================================================
# API Endpoints
# ============================================================

@app.post(
    "/api/chat",
    response_model=ChatResponse,
    summary="Kirim prompt untuk diperiksa guardrail dan diteruskan ke chatbot",
)
async def chat_endpoint(request: ChatRequest):
    """
    Endpoint utama yang:
    1. Menerima prompt dari Web Chat UI
    2. Mengklasifikasikannya dengan model ONNX guardrail
    3. Jika injection terdeteksi (confidence >= threshold): BLOKIR (HTTP 403)
    4. Jika aman: Teruskan ke Ollama dan kembalikan balasan chatbot
    """
    total_start = time.perf_counter()

    # Gunakan threshold dari request atau default dari config
    threshold = request.threshold if request.threshold is not None else settings.default_threshold

    # --- Langkah 1: Klasifikasi prompt dengan guardrail ---
    result = detector.predict(request.prompt, threshold=threshold)

    if result.is_injection:
        # === BLOKIR: Prompt terdeteksi sebagai injection ===
        total_ms = (time.perf_counter() - total_start) * 1000.0

        response_data = ChatResponse(
            status="blocked",
            is_injection=True,
            confidence_score=result.confidence_score,
            threshold_used=result.threshold_used,
            guardrail_latency_ms=result.guardrail_latency_ms,
            total_latency_ms=round(total_ms, 2),
            message="Permintaan ditolak oleh sistem pertahanan: Terdeteksi upaya Prompt Injection.",
            bot_reply=None,
        )

        # Catat ke log keamanan
        security_logger.log_event(
            prompt=request.prompt,
            confidence_score=result.confidence_score,
            threshold_used=result.threshold_used,
            is_injection=True,
            status="blocked",
            guardrail_latency_ms=result.guardrail_latency_ms,
            total_latency_ms=round(total_ms, 2),
        )

        log.warning(
            f"🚫 BLOCKED | Skor: {result.confidence_score:.4f} | "
            f"Prompt: {request.prompt[:80]}..."
        )

        # Fail-Closed: Kembalikan HTTP 403 Forbidden
        return JSONResponse(
            status_code=403,
            content=response_data.model_dump(),
        )

    # === AMAN: Teruskan prompt ke Ollama ===
    bot_reply = None
    try:
        bot_reply = await ollama_client.chat(request.prompt)
    except ConnectionError:
        bot_reply = "[Error] Tidak dapat terhubung ke layanan chatbot. Silakan coba lagi nanti."
    except TimeoutError:
        bot_reply = "[Error] Waktu tunggu chatbot habis. Silakan coba pertanyaan yang lebih singkat."
    except Exception as e:
        log.error(f"Error saat komunikasi dengan Ollama: {e}")
        bot_reply = "[Error] Terjadi kesalahan pada layanan chatbot."

    total_ms = (time.perf_counter() - total_start) * 1000.0

    response_data = ChatResponse(
        status="allowed",
        is_injection=False,
        confidence_score=result.confidence_score,
        threshold_used=result.threshold_used,
        guardrail_latency_ms=result.guardrail_latency_ms,
        total_latency_ms=round(total_ms, 2),
        message="Prompt aman dan telah diteruskan ke asisten AI.",
        bot_reply=bot_reply,
    )

    # Catat ke log keamanan
    security_logger.log_event(
        prompt=request.prompt,
        confidence_score=result.confidence_score,
        threshold_used=result.threshold_used,
        is_injection=False,
        status="allowed",
        guardrail_latency_ms=result.guardrail_latency_ms,
        total_latency_ms=round(total_ms, 2),
        bot_reply=bot_reply,
    )

    log.info(
        f"✅ ALLOWED | Skor: {result.confidence_score:.4f} | "
        f"Prompt: {request.prompt[:80]}..."
    )

    return response_data


@app.get(
    "/api/health",
    response_model=HealthResponse,
    summary="Periksa kesiapan sistem guardrail dan konektivitas Ollama",
)
async def health_endpoint():
    """
    Health check endpoint untuk memastikan:
    - Model ONNX sudah termuat di memori
    - Container Ollama dapat dijangkau melalui jaringan internal
    """
    ollama_ok = await ollama_client.health_check()

    return HealthResponse(
        status="healthy" if (detector.is_loaded and ollama_ok) else "degraded",
        model_loaded=detector.is_loaded,
        model_mode="mock" if detector.is_mock else "onnx",
        ollama_connected=ollama_ok,
        threshold=settings.default_threshold,
        ollama_model=settings.ollama_model,
    )


# ============================================================
# Static Files Mount — Web Chat UI
# ============================================================
# Harus di-mount TERAKHIR agar tidak mengoverride route API.
# Menyajikan index.html, style.css, app.js dari folder static/
# pada URL root (http://localhost:8000/)
# ============================================================

app.mount("/", StaticFiles(directory="static", html=True), name="static")
