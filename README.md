# hermes-mimo-tts

A [Hermes Agent](https://hermes-agent.nousresearch.com) TTS plugin that integrates Xiaomi's **MiMo-V2.5-TTS** as a drop-in speech provider.

## Features

- Three MiMo models: preset voices / text-described voice design / audio-sample clone
- 9 preset voices: 5 Chinese (冰糖 / 茉莉 / 苏打 / 白桦 / default) and 4 English (Mia / Chloe / Milo / Dean)
- Natural-language style control via an optional `style` directive
- Automatic format conversion (WAV → MP3 / OGG / FLAC) using `ffmpeg`
- Shows up in `hermes tools` Voice & TTS picker

## Prerequisites

| Requirement | Notes |
|---|---|
| [Hermes Agent](https://hermes-agent.nousresearch.com) | v0.10.0 or later |
| MiMo API key | Get one at [platform.xiaomimimo.com](https://platform.xiaomimimo.com) |
| `ffmpeg` | Only required when output format is not WAV |

## Installation

**Recommended — install directly from GitHub:**

```bash
hermes plugins install Stark-X/hermes-mimo-tts --enable
```

Hermes clones the repo into `~/.hermes/plugins/mimo-tts/`, prompts for `MIMO_API_KEY`,
and enables the plugin in one step.

**Alternative — manual clone + symlink (for development or local edits):**

```bash
git clone https://github.com/Stark-X/hermes-mimo-tts.git
ln -s "$(pwd)/hermes-mimo-tts" ~/.hermes/plugins/mimo-tts
hermes plugins enable mimo-tts
```

## Configuration

Add the following to `~/.hermes/config.yaml`:

```yaml
tts:
  provider: mimo          # activate this plugin

  mimo:
    # MiMo model to use. Valid values:
    #   mimo-v2.5-tts             — preset voices (default)
    #   mimo-v2.5-tts-voicedesign — voice generated from a text description (set via `style`)
    #   mimo-v2.5-tts-voiceclone  — voice cloned from a base64-encoded audio sample (set via `voice`)
    model: "mimo-v2.5-tts"

    # Voice ID to use when no voice is specified by the caller.
    # For mimo-v2.5-tts: any id from the preset voice table below.
    # For mimo-v2.5-tts-voiceclone: base64 audio data URL
    #   (format: "data:audio/mpeg;base64,<base64_string>").
    # Ignored for mimo-v2.5-tts-voicedesign.
    voice: "Chloe"

    # Natural-language style / tone directive sent as the `user` message.
    # For mimo-v2.5-tts-voicedesign: this is the voice description and is required.
    # For other models: optional — leave empty to skip.
    # Example: "用温柔低沉的语调，语速缓慢，带着一丝疲惫"
    style: ""

    # MiMo API base URL. Change to a closer regional endpoint if needed.
    # Singapore: https://token-plan-sgp.xiaomimimo.com/v1
    base_url: "https://token-plan-sgp.xiaomimimo.com/v1"

    # Hard client-side character cap. Text longer than this is silently
    # truncated before being sent to the API, preventing 400 errors.
    max_text_length: 4096

    # HTTP request timeout in seconds for each MiMo API call.
    timeout: 60
```

Set your API key in `~/.hermes/.env` (Hermes loads this file automatically on startup):

```bash
# ~/.hermes/.env
MIMO_API_KEY=your_api_key_here
```

Create the file if it doesn't exist:

```bash
echo 'MIMO_API_KEY=your_api_key_here' >> ~/.hermes/.env
```

## Models

| Model ID | Description | `voice` | `style` |
|---|---|---|---|
| `mimo-v2.5-tts` | Preset voices (default) | Preset voice ID (see table below) | Optional — tone/style directive |
| `mimo-v2.5-tts-voicedesign` | Generate a voice from a text description | Ignored | **Required** — voice description |
| `mimo-v2.5-tts-voiceclone` | Clone a voice from an audio sample | Base64 audio data URL | Optional — tone/style directive |

### mimo-v2.5-tts — Preset Voices

| Voice ID | Language | Gender |
|---|---|---|
| `mimo_default` | zh (default varies by cluster) | female |
| `冰糖` | Chinese | Female |
| `茉莉` | Chinese | Female |
| `苏打` | Chinese | Male |
| `白桦` | Chinese | Male |
| `Mia` | English | Female |
| `Chloe` | English | Female |
| `Milo` | English | Male |
| `Dean` | English | Male |

Run `hermes tools` → **Voice & TTS** to browse voices interactively.

### mimo-v2.5-tts-voicedesign — Voice Design

Set `model: mimo-v2.5-tts-voicedesign` and describe the voice in `style`:

```yaml
tts:
  mimo:
    model: "mimo-v2.5-tts-voicedesign"
    style: "Young female, warm and confident, moderate pace, slight Taiwanese accent"
```

### mimo-v2.5-tts-voiceclone — Voice Clone

Set `model: mimo-v2.5-tts-voiceclone` and supply a base64-encoded MP3/WAV sample as `voice`:

```yaml
tts:
  mimo:
    model: "mimo-v2.5-tts-voiceclone"
    voice: "data:audio/mpeg;base64,<your_base64_string>"
```

Generate the base64 string from a local file:

```bash
python3 -c "import base64; print('data:audio/mpeg;base64,' + base64.b64encode(open('sample.mp3','rb').read()).decode())"
```

## Style Control

The `style` field maps to MiMo's natural-language style directive (the `user` message). A few examples:

```yaml
# Lively and upbeat
style: "用轻快上扬的语调，语速稍快，充满活力"

# Calm broadcast style
style: "磁性低沉的男声，如同深夜电台主播，语速平稳"

# Emotional, slightly tired
style: "温柔但带着一丝疲惫，像是长途旅行后的心情"
```

MiMo also supports inline audio tags in the text itself for word-level control:

```
（深呼吸）好，冷静一下……（语速加快）没问题的，我可以的！
```

## Usage

Hermes does not expose a standalone `tts` subcommand. TTS is triggered by the agent
during a conversation when it decides to speak a response aloud. Start a session and
ask the agent to read something:

```bash
hermes
```

Then in the conversation:

```
> 用语音朗读：今天天气真不错。
> Please read this aloud: Hello, this is MiMo speaking.
> 帮我用茉莉音色说一句话
```

The agent will call the `text_to_speech` tool internally and deliver audio according
to the platform (CLI saves to `~/.hermes/audio_cache/`, Telegram sends a voice bubble,
etc.).

To verify the plugin is loaded before starting a conversation:

```bash
hermes plugins list        # mimo-tts should appear as enabled
hermes tools               # Voice & TTS picker should show "Xiaomi MiMo"
```

## License

MIT
