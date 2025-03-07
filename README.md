# OBS Prometheus Exporter

Exporter for OBS Studio metrics via WebSocket to Prometheus.

## Features

- Export OBS Studio metrics to Prometheus
- Support for Windows/Linux/macOS

## Requirements

- Python 3.11+

## Installation

```bash
pip install -r requirements.txt

## Usage

```bash
python obs_exporter.py --obs_host localhost --obs_port 4455 --prometheus_exporter_port 9000
```

### Prometheus

Configure your Prometheus to scrape metrics from:

```
http://localhost:9000
```

## Metrics

- CPU usage
- Memory usage
- Active FPS
- Render times
- Output statuses and more.

## Build Executable (Windows)

Executable files are automatically generated and available under GitHub Actions artifacts for tagged releases.

## License

MIT License - see [LICENSE](LICENSE) file.