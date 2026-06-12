from __future__ import annotations

import base64
import os
from abc import ABC, abstractmethod
from typing import Any

from .models import VoiceResult


class VoiceProvider(ABC):
    @abstractmethod
    def stt(self, audio_base64: str, format: str = "wav") -> VoiceResult:
        ...

    @abstractmethod
    def tts(self, text: str, format: str = "wav") -> VoiceResult:
        ...


class MockVoiceProvider(VoiceProvider):
    def stt(self, audio_base64: str, format: str = "wav") -> VoiceResult:
        try:
            decoded = base64.b64decode(audio_base64)
            text = f"[mock stt from {len(decoded)} bytes of {format}]"
            return VoiceResult(ok=True, text=text, format=format)
        except Exception as exc:
            return VoiceResult(ok=False, text="", format=format, error=str(exc))

    def tts(self, text: str, format: str = "wav") -> VoiceResult:
        preamble = f"Spoken: {text[:100]}"
        audio_bytes = preamble.encode("utf-8").ljust(1024, b"\x00")
        audio_b64 = base64.b64encode(audio_bytes).decode("ascii")
        return VoiceResult(ok=True, text="", format=format, audio_base64=audio_b64)


class GeminiVoiceProvider(VoiceProvider):
    def __init__(self) -> None:
        import google.genai as genai

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY not set")
        self._client = genai.Client(api_key=api_key)

    def stt(self, audio_base64: str, format: str = "wav") -> VoiceResult:
        try:
            import google.genai.types as types

            audio_bytes = base64.b64decode(audio_base64)
            # Gemini 2.0 Flash accepts inline audio data
            response = self._client.models.generate_content(
                model="gemini-2.0-flash",
                contents=[
                    types.Content(
                        parts=[
                            types.Part(inline_data=types.Blob(mime_type=f"audio/{format}", data=audio_bytes)),
                            types.Part(text="Transcribe this audio verbatim."),
                        ]
                    ),
                ],
            )
            text = response.text.strip()
            return VoiceResult(ok=bool(text), text=text, format=format)
        except Exception as exc:
            return VoiceResult(ok=False, text="", format=format, error=str(exc))

    def tts(self, text: str, format: str = "wav") -> VoiceResult:
        try:
            import google.genai.types as types

            response = self._client.models.generate_content(
                model="gemini-2.0-flash",
                contents=[
                    types.Content(
                        parts=[
                            types.Part(text=f"Generate speech audio for: {text}"),
                        ]
                    ),
                ],
                config=types.GenerateContentConfig(
                    response_modalities=["Audio"],
                ),
            )
            audio_b64 = ""
            if response.candidates and response.candidates[0].content.parts:
                for part in response.candidates[0].content.parts:
                    if part.inline_data and part.inline_data.data:
                        audio_b64 = base64.b64encode(part.inline_data.data).decode("ascii")
                        break
            return VoiceResult(ok=bool(audio_b64), audio_base64=audio_b64, format=format)
        except Exception as exc:
            return VoiceResult(ok=False, text="", format=format, error=str(exc))


def make_voice_provider() -> VoiceProvider:
    if os.getenv("GEMINI_API_KEY"):
        try:
            return GeminiVoiceProvider()
        except Exception:
            pass
    return MockVoiceProvider()
