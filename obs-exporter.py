import argparse
import logging
import signal
import sys
from time import sleep

import obsws_python as obs
from prometheus_client import start_http_server
from prometheus_client.core import GaugeMetricFamily, REGISTRY, CounterMetricFamily

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Argument parser setup
parser = argparse.ArgumentParser(
    description="OBS Exporter: Export OBS Studio metrics to Prometheus."
)

parser.add_argument(
    "--obs_host",
    type=str,
    default="localhost",
    help="OBS Studio WebSocket host (default: localhost)."
)
parser.add_argument(
    "--obs_port",
    type=int,
    default=4455,
    help="OBS Studio WebSocket port (default: 4455)."
)
parser.add_argument(
    "--prometheus_exporter_port",
    type=int,
    default=9000,
    help="Port for Prometheus metrics (default: 9000)."
)

args = parser.parse_args()
obs_host = args.obs_host
obs_port = args.obs_port
exporter_port = args.prometheus_exporter_port


def connect_obs() -> obs.ReqClient:
    """Attempt to establish a connection to OBS WebSocket."""
    while True:
        try:
            obs_connection = obs.ReqClient(host=obs_host, port=obs_port, password='', timeout=3)
            logging.info("Successfully connected to OBS")
            return obs_connection
        except Exception as e:
            logging.error(f"Failed to connect to OBS: {e}")
            sleep(3)


class DefaultObsCollector:
    """Default collector that provides basic connection metric."""
    def collect(self):
        gauge = GaugeMetricFamily("obsgauge", "Default OBS connection gauge", labels=["metric"])
        gauge.add_metric(['obsConnection'], 0.0)
        yield gauge


class ObsCollector(object):
    """Custom Prometheus collector to export OBS metrics."""

    def __init__(self, client: obs.ReqClient):
        self.client = client

    def collect(self):
        """Collect metrics from OBS and yield them to Prometheus."""
        stats = self.client.send("GetStats", raw=True)
        output_list = self.client.get_output_list().outputs
        first_active_output = next((item for item in output_list if item.get('outputActive')), None)

        gauge = GaugeMetricFamily("obsgauge", "OBS metrics gauge", labels=["metric"])
        gauge.add_metric(['obsConnection'], 1.0)
        gauge.add_metric(['cpuUsage'], stats["cpuUsage"])
        gauge.add_metric(["memoryUsage"], stats["memoryUsage"])
        gauge.add_metric(["activeFps"], stats["activeFps"])
        gauge.add_metric(["averageFrameRenderTime"], stats["averageFrameRenderTime"])

        is_active = 0.0
        output_congestion = 0.0
        output_duration = 0.0
        output_reconnecting = 0.0
        output_skipped_frames = 0.0
        output_total_frames = 0.0

        if first_active_output:
            output_stats = self.client.send("GetOutputStatus", {"outputName": first_active_output["outputName"]}, raw=True)
            is_active = 1.0
            output_congestion = output_stats["outputCongestion"]
            output_duration = output_stats["outputDuration"]
            output_reconnecting = float(output_stats["outputReconnecting"])
            output_skipped_frames = output_stats["outputSkippedFrames"]
            output_total_frames = output_stats["outputTotalFrames"]

        gauge.add_metric(["outputActive"], is_active)
        gauge.add_metric(["outputReconnecting"], output_reconnecting)
        gauge.add_metric(["outputCongestion"], output_congestion)

        yield gauge

        count = CounterMetricFamily("obscounter", "OBS metrics counter", labels=['metric'])
        count.add_metric(['renderSkippedFrames'], stats["renderSkippedFrames"])
        count.add_metric(['renderTotalFrames'], stats["renderTotalFrames"])
        count.add_metric(["outputSkippedFrames"], stats["outputSkippedFrames"])
        count.add_metric(["outputTotalFrames"], stats["outputTotalFrames"])

        count.add_metric(["outputDuration"], output_duration)
        count.add_metric(["outputSkippedFrames"], output_skipped_frames)
        count.add_metric(["outputTotalFrames"], output_total_frames)

        yield count


def clear_registry():
    """Clear all collectors from Prometheus registry."""
    collectors = list(REGISTRY._collector_to_names.keys())
    for collector in collectors:
        REGISTRY.unregister(collector)


running = True


def signal_handler(sig, frame):
    """Handle termination signals to gracefully shutdown."""
    global running
    logging.info("Shutting down OBS Exporter gracefully...")
    running = False
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


def main():
    """Main loop: Connect to OBS and continuously export metrics."""
    clear_registry()
    default_collector = DefaultObsCollector()
    REGISTRY.register(default_collector)

    obs_connection = connect_obs()

    clear_registry()
    collector = ObsCollector(obs_connection)
    REGISTRY.register(collector)

    version = obs_connection.get_version().obs_version
    logging.info(f"OBS Version: {version}")

    while running:
        try:
            obs_connection.get_version()
        except Exception as e:
            logging.error(f"Lost connection to OBS: {e}")
            break
        sleep(5)


if __name__ == '__main__':
    start_http_server(addr="127.0.0.1", port=exporter_port)
    logging.info(f"Prometheus exporter running at 127.0.0.1:{exporter_port}")

    while running:
        main()
        sleep(5)