# hermes-mimo-tts

A [Hermes Agent](https://hermes-agent.nousresearch.com) TTS plugin that integrates Xiaomi's **MiMo-V2.5-TTS** (preset voices) as a drop-in speech provider.

## Features

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

```bash
# 1. Clone the repo
git clone https://github.com/Stark-X/hermes-mimo-tts.git

# 2. Symlink into Hermes plugins directory
ln -s "$(pwd)/hermes-mimo-tts" ~/.hermes/plugins/mimo-tts

# 3. Enable the plugin
hermes plugins enable mimo-tts
```

## Configuration

Add the following to `~/.hermes/config.yaml`:

```yaml
tts:
  provider: mimo          # activate this plugin

  mimo:
    # Voice ID to use when no voice is specified by the caller.
    # Valid values: mimo_default | 冰糖 | 茉莉 | 苏打 | 白桦 | Mia | Chloe | Milo | Dean
    voice: "Chloe"

    # Optional natural-language style directive passed as the `user` message.
    # Supports tone, emotion, pacing — leave empty for no style control.
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

Set your API key in the environment:

```bash
export MIMO_API_KEY=your_api_key_here
```

Or add it to your shell profile (`~/.bashrc`, `~/.zshrc`, etc.) for persistence.

## Available Voices

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

Run `hermes tools` → **Voice & TTS** to browse and preview voices interactively.

## Style Control

The `style` field maps to MiMo's natural-language style directive. A few examples:

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

```bash
# Basic
hermes tts "Hello, this is MiMo speaking."

# One-off voice override
hermes tts --voice 冰糖 "你好，这是冰糖音色。"
```

## License

MIT
