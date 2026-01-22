# ShutterSense Agent

Distributed agent for ShutterSense photo processing pipeline.

## Installation

### Development Mode

```bash
cd agent
pip install -e .
```

### Build Standalone Binary

```bash
# macOS
./packaging/build_macos.sh

# Linux
./packaging/build_linux.sh

# Windows
./packaging/build_windows.sh
```

## Usage

### 1. Register the Agent

Get a registration token from the ShutterSense web UI (Settings > Agents), then:

```bash
shuttersense-agent register \
  --server http://your-server:8000 \
  --token art_xxxxx... \
  --name "My Agent"
```

### 2. Start the Agent

```bash
shuttersense-agent start
```

The agent will connect to the server and begin polling for jobs.

## Commands

| Command | Description |
|---------|-------------|
| `register` | Register agent with ShutterSense server |
| `start` | Start the agent polling loop |

## Configuration

Agent configuration is stored in platform-specific locations:
- **macOS**: `~/Library/Application Support/shuttersense-agent/`
- **Linux**: `~/.config/shuttersense-agent/`
- **Windows**: `%APPDATA%\shuttersense-agent\`

## Requirements

- Python 3.10+
- Network access to ShutterSense server

## License

AGPL-3.0
