"""
Hermes Agent TTS plugin — Xiaomi MiMo-V2.5-TTS.

Supported models:
  mimo-v2.5-tts           — preset voices (default)
  mimo-v2.5-tts-voicedesign — voice generated from a text description (set via `style`)
  mimo-v2.5-tts-voiceclone  — voice cloned from a base64-encoded audio sample (set via `voice`)

Requires:
  - MIMO_API_KEY environment variable
  - openai Python package (already bundled in the Hermes venv)
  - ffmpeg in PATH (only needed when output format is not WAV)
"""

import base64
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import yaml

try:
    from agent.tts_provider import TTSProvider
except ImportError:
    # allow static import / unit testing outside the Hermes runtime
    class TTSProvider:  # type: ignore[no-redef]
        pass


_CONFIG_PATH = Path.home() / ".hermes" / "config.yaml"

# All preset voices documented at:
# https://platform.xiaomimimo.com/docs/zh-CN/usage-guide/speech-synthesis-v2.5
_PRESET_VOICES = [
    {"id": "mimo_default", "display": "MiMo 默认", "language": "zh", "gender": "female", "preview_url": None},
    {"id": "冰糖",          "display": "冰糖",       "language": "zh", "gender": "female", "preview_url": None},
    {"id": "茉莉",          "display": "茉莉",       "language": "zh", "gender": "female", "preview_url": None},
    {"id": "苏打",          "display": "苏打",       "language": "zh", "gender": "male",   "preview_url": None},
    {"id": "白桦",          "display": "白桦",       "language": "zh", "gender": "male",   "preview_url": None},
    {"id": "Mia",           "display": "Mia",        "language": "en", "gender": "female", "preview_url": None},
    {"id": "Chloe",         "display": "Chloe",      "language": "en", "gender": "female", "preview_url": None},
    {"id": "Milo",          "display": "Milo",       "language": "en", "gender": "male",   "preview_url": None},
    {"id": "Dean",          "display": "Dean",       "language": "en", "gender": "male",   "preview_url": None},
]

_DEFAULT_BASE_URL = "https://token-plan-sgp.xiaomimimo.com/v1"
_DEFAULT_MODEL = "mimo-v2.5-tts"

# Models that must NOT receive a `voice` key in the audio dict
_VOICEDESIGN_MODELS = {"mimo-v2.5-tts-voicedesign"}


def _load_mimo_config() -> dict[str, Any]:
    """Read the tts.mimo section from ~/.hermes/config.yaml, silently return {} on any error."""
    try:
        with open(_CONFIG_PATH, encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
        return cfg.get("tts", {}).get("mimo", {})
    except Exception:
        return {}


class MimoTTSProvider(TTSProvider):
    # MiMo returns WAV; Hermes handles the WAV→Opus conversion for
    # Telegram voice bubbles when voice_compatible=False (the default).
    voice_compatible = False

    @property
    def name(self) -> str:
        # Must match tts.provider value in config.yaml
        return "mimo"

    @property
    def display_name(self) -> str:
        return "Xiaomi MiMo TTS"

    def is_available(self) -> bool:
        """Return True only when the API key is set and the openai SDK is importable."""
        if not os.environ.get("MIMO_API_KEY"):
            return False
        try:
            import openai  # noqa: F401
            return True
        except ImportError:
            return False

    def list_voices(self) -> list[dict]:
        return list(_PRESET_VOICES)

    def list_models(self) -> list[dict]:
        return [
            {
                "id": "mimo-v2.5-tts",
                "display": "MiMo-V2.5-TTS (preset voices)",
                "languages": ["zh", "en"],
                "max_text_length": 4096,
            },
            {
                "id": "mimo-v2.5-tts-voicedesign",
                "display": "MiMo-V2.5-TTS VoiceDesign (text-described voice)",
                "languages": ["zh", "en"],
                "max_text_length": 4096,
            },
            {
                "id": "mimo-v2.5-tts-voiceclone",
                "display": "MiMo-V2.5-TTS VoiceClone (audio-sample clone)",
                "languages": ["zh", "en"],
                "max_text_length": 4096,
            },
        ]

    def get_setup_schema(self) -> dict:
        """Powers the provider row in `hermes tools` / `hermes setup`."""
        return {
            "name": "Xiaomi MiMo",
            "badge": "Paid",
            "tag": "mimo",
            "env_vars": [
                {
                    "key": "MIMO_API_KEY",
                    "prompt": "Enter your MiMo API key",
                    "url": "https://platform.xiaomimimo.com",
                }
            ],
        }

    def synthesize(
        self,
        text: str,
        output_path: str,
        *,
        voice: str | None = None,
        model: str | None = None,
        speed: float | None = None,
        format: str = "mp3",
        **extra: Any,
    ) -> str:
        """
        Synthesize *text* and write the audio to *output_path*.

        Config values are read from the tts.mimo section of config.yaml at
        call time so the user can change them without restarting Hermes.
        """
        from openai import OpenAI

        cfg = _load_mimo_config()

        # MiMo model to use. Caller's model= arg takes precedence over config.
        # Valid values: mimo-v2.5-tts | mimo-v2.5-tts-voicedesign | mimo-v2.5-tts-voiceclone
        resolved_model: str = model or cfg.get("model", _DEFAULT_MODEL)

        # Voice ID (preset model) or base64 audio data URL (voiceclone model).
        # Ignored when using mimo-v2.5-tts-voicedesign.
        default_voice: str = cfg.get("voice", "Chloe")

        # Natural-language style / tone directive sent as the `user` message.
        # For mimo-v2.5-tts-voicedesign this field is the voice description and
        # is required. For other models it is optional.
        # Example: "用温柔低沉的语调，语速缓慢"
        style: str = cfg.get("style", "")

        # MiMo API base URL — change this if using a different regional endpoint.
        base_url: str = cfg.get("base_url", _DEFAULT_BASE_URL)

        # Hard client-side cap on input text length (characters) to avoid API
        # 400 errors. Hermes truncates before calling; does not raise.
        max_text_length: int = int(cfg.get("max_text_length", 4096))

        # HTTP request timeout in seconds for the MiMo API call.
        timeout: int = int(cfg.get("timeout", 60))

        api_key = os.environ.get("MIMO_API_KEY")
        if not api_key:
            raise RuntimeError("MiMo TTS failed: MIMO_API_KEY environment variable is not set")

        text = text[:max_text_length]
        resolved_voice = voice or default_voice

        # MiMo places the text-to-synthesize in the `assistant` role.
        # An optional (or required, for voicedesign) `user` message carries
        # the style directive or voice description.
        messages: list[dict] = []
        if style:
            messages.append({"role": "user", "content": style})
        messages.append({"role": "assistant", "content": text})

        # voicedesign generates its own voice from the style description —
        # passing a `voice` key would be ignored or cause an error.
        if resolved_model in _VOICEDESIGN_MODELS:
            audio_params: dict = {"format": "wav"}
        else:
            audio_params = {"format": "wav", "voice": resolved_voice}

        try:
            client = OpenAI(api_key=api_key, base_url=base_url, timeout=timeout)
            completion = client.chat.completions.create(
                model=resolved_model,
                messages=messages,
                audio=audio_params,
            )
            audio_data = completion.choices[0].message.audio
            if audio_data is None:
                raise RuntimeError("MiMo returned no audio data in the response")
            wav_bytes = base64.b64decode(audio_data.data)
        except Exception as exc:
            raise RuntimeError(f"MiMo TTS failed: {exc}") from exc

        # Fast path: caller wants WAV — write directly, no ffmpeg needed.
        if format == "wav":
            Path(output_path).write_bytes(wav_bytes)
            return output_path

        # General path: transcode WAV → requested format via ffmpeg.
        tmp_wav = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                tmp_wav = f.name
                f.write(wav_bytes)
            subprocess.run(
                ["ffmpeg", "-y", "-loglevel", "error", "-i", tmp_wav, output_path],
                check=True,
            )
        except subprocess.CalledProcessError as exc:
            raise RuntimeError(f"MiMo TTS: ffmpeg conversion failed: {exc}") from exc
        finally:
            if tmp_wav and os.path.exists(tmp_wav):
                os.unlink(tmp_wav)

        return output_path


def register(ctx) -> None:
    ctx.register_tts_provider(MimoTTSProvider())
