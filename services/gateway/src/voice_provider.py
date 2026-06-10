from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Protocol

from .schemas import (
    VoiceSentimentRequest,
    VoiceSentimentResult,
    VoiceSynthesisRequest,
    VoiceSynthesisResult,
    VoiceTranscriptionRequest,
    VoiceTranscriptionResult,
)


class STTProvider(Protocol):
    async def transcribe(self, payload: VoiceTranscriptionRequest) -> VoiceTranscriptionResult: ...


class TTSProvider(Protocol):
    async def synthesize(self, payload: VoiceSynthesisRequest) -> VoiceSynthesisResult: ...


@dataclass
class ProviderFlags:
    enable_whisper: bool
    enable_piper: bool


def _parse_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on", "enabled"}


def get_provider_flags() -> ProviderFlags:
    return ProviderFlags(
        enable_whisper=_parse_bool(os.getenv("ENABLE_WHISPER"), default=False),
        enable_piper=_parse_bool(os.getenv("ENABLE_PIPER"), default=False),
    )


class PlaceholderSTT:
    async def transcribe(self, payload: VoiceTranscriptionRequest) -> VoiceTranscriptionResult:
        # Existing gateway already has a deterministic local implementation.
        # This placeholder keeps API contract intact when containers are disabled.
        transcript = payload.audio_text.strip()
        speaker = payload.speaker_hint or ("Keerthi" if "keerthi" in transcript.lower() else "unknown")
        return VoiceTranscriptionResult(
            transcript=transcript,
            confidence=92 if len(transcript.split()) >= 3 else 76,
            speaker=speaker,
            wake_word_detected="jarvis" in transcript.lower() or "shiva" in transcript.lower(),
        )


class PlaceholderTTS:
    async def synthesize(self, payload: VoiceSynthesisRequest) -> VoiceSynthesisResult:
        return VoiceSynthesisResult(
            text=payload.text,
            voice_id=payload.voice_id,
            format="browser-speech",
            audio_url=None,
            browser_speech_supported=True,
        )


class LocalVoiceProvider:
    """Voice provider router.

    When ENABLE_WHISPER/ENABLE_PIPER are false, we default to placeholders so
    the platform stays functional without voice containers.

    Future work: implement HTTP adapters to the whisper/piper containers.
    """

    def __init__(self, flags: ProviderFlags | None = None):
        self.flags = flags or get_provider_flags()
        self.stt: STTProvider = PlaceholderSTT()
        self.tts: TTSProvider = PlaceholderTTS()

    async def transcribe(self, payload: VoiceTranscriptionRequest) -> VoiceTranscriptionResult:
        return await self.stt.transcribe(payload)

    async def synthesize(self, payload: VoiceSynthesisRequest) -> VoiceSynthesisResult:
        return await self.tts.synthesize(payload)

    async def sentiment(self, payload: VoiceSentimentRequest) -> VoiceSentimentResult:
        # Sentiment remains a local deterministic function for now.
        text = payload.transcript.lower()
        urgent_terms = {"urgent", "asap", "critical", "blocked", "failed", "now"}
        positive_terms = {"great", "good", "done", "thanks", "perfect"}
        urgency = min(95, 25 + sum(1 for term in urgent_terms if term in text) * 20)
        sentiment = "positive" if any(term in text for term in positive_terms) else "neutral"
        if urgency >= 65:
            sentiment = "urgent"
        return VoiceSentimentResult(
            sentiment=sentiment,
            energy="high" if "!" in payload.transcript or urgency >= 65 else "steady",
            urgency_score=urgency,
        )

