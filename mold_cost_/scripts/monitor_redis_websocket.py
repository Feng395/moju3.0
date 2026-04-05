"""Redis and websocket message monitor script."""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
for path in (str(SRC), str(ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

from mold_cost.core.settings import settings
from mold_cost.infrastructure.messaging.monitor_websocket import RedisWebSocketActivityTracker
from mold_cost.infrastructure.messaging.redis_client import redis_client


class Colors:
    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


def print_header(text: str):
    print(f"\n{Colors.BOLD}{Colors.HEADER}{'=' * 80}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.HEADER}{text:^80}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.HEADER}{'=' * 80}{Colors.ENDC}\n")


def print_redis_message(channel: str, data: dict[str, Any]):
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"{Colors.CYAN}[{timestamp}] Redis message{Colors.ENDC}")
    print(f"{Colors.BLUE}  channel: {channel}{Colors.ENDC}")

    parts = channel.split(":")
    if len(parts) >= 2:
        print(f"{Colors.BLUE}  job_id: {parts[1]}{Colors.ENDC}")

    print(f"{Colors.GREEN}  payload:{Colors.ENDC}")
    for key, value in data.items():
        print(f"    {Colors.YELLOW}{key:20s}{Colors.ENDC}: {value}")

    print(f"{Colors.CYAN}{'─' * 80}{Colors.ENDC}")


def print_websocket_push(job_id: str, message: dict[str, Any], connection_count: int):
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"{Colors.GREEN}[{timestamp}] WebSocket activity{Colors.ENDC}")
    print(f"{Colors.BLUE}  job_id: {job_id}{Colors.ENDC}")
    print(f"{Colors.BLUE}  active jobs: {connection_count}{Colors.ENDC}")
    print(f"{Colors.GREEN}  message:{Colors.ENDC}")
    print(f"    {Colors.YELLOW}{'type':20s}{Colors.ENDC}: {message.get('type')}")
    print(f"    {Colors.YELLOW}{'timestamp':20s}{Colors.ENDC}: {message.get('timestamp')}")

    if 'data' in message:
        print(f"    {Colors.YELLOW}{'data':20s}{Colors.ENDC}:")
        for key, value in message['data'].items():
            print(f"      {Colors.YELLOW}{key:18s}{Colors.ENDC}: {value}")

    print(f"{Colors.GREEN}{'─' * 80}{Colors.ENDC}")


def print_connection_change(event: str, job_id: str, count: int):
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    if event == "connect":
        emoji = "✅"
        color = Colors.GREEN
        text = "connection active"
    else:
        emoji = "❌"
        color = Colors.RED
        text = "connection inactive"

    print(f"{color}[{timestamp}] {emoji} {text}{Colors.ENDC}")
    print(f"{Colors.BLUE}  job_id: {job_id}{Colors.ENDC}")
    print(f"{Colors.BLUE}  active jobs: {count}{Colors.ENDC}")
    print(f"{color}{'─' * 80}{Colors.ENDC}")


def print_error(error: str):
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"{Colors.RED}[{timestamp}] error: {error}{Colors.ENDC}")


def print_info(info: str):
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"{Colors.CYAN}[{timestamp}] {info}{Colors.ENDC}")


def _extract_job_id(channel: str) -> str | None:
    parts = channel.split(":")
    return parts[1] if len(parts) >= 2 else None


async def monitor_redis():
    print_header("Redis message monitor")

    try:
        print_info(f"connecting to Redis: {settings.REDIS_URL}")
        await redis_client.connect()
        pubsub = await redis_client.subscribe("job:*:progress")
        print_info("Redis connected")
        print_info("subscribed: job:*:progress")
        print_info("listening for messages...")
        print(f"{Colors.YELLOW}{'─' * 80}{Colors.ENDC}\n")

        message_count = 0
        async for message in pubsub.listen():
            if message['type'] != 'pmessage':
                continue

            message_count += 1
            channel = message['channel']
            if isinstance(channel, bytes):
                channel = channel.decode('utf-8')

            data_str = message['data']
            if isinstance(data_str, bytes):
                data_str = data_str.decode('utf-8')

            try:
                data = json.loads(data_str)
                print_redis_message(channel, data)

                job_id = _extract_job_id(channel)
                if job_id:
                    ws_message = {
                        "type": "progress",
                        "job_id": job_id,
                        "timestamp": datetime.now().isoformat(),
                        "data": data,
                    }
                    print_websocket_push(job_id, ws_message, 1)

                print(f"\n{Colors.BOLD}total messages: {message_count}{Colors.ENDC}\n")
            except json.JSONDecodeError as exc:
                print_error(f"JSON parse failed: {exc}")

    except KeyboardInterrupt:
        print_info("monitor interrupted by user")
    except Exception as exc:
        print_error(f"monitor failed: {exc}")
        import traceback

        traceback.print_exc()
    finally:
        await redis_client.close()
        print_info("Redis connection closed")


async def monitor_websocket_connections():
    print_header("WebSocket activity monitor")

    tracker = RedisWebSocketActivityTracker(activity_timeout_seconds=5)
    last_connections: dict[str, int] = {}

    async def prune_loop():
        while True:
            await asyncio.sleep(1)
            expired = tracker.prune_stale()
            for job_id in expired:
                print_connection_change("disconnect", job_id, 0)

    try:
        await redis_client.connect()
        pubsub = await redis_client.subscribe("job:*:progress", "job:*:review")
        print_info("monitoring Redis channels: job:*:progress, job:*:review")
        print_info("live websocket count is best-effort and based on recent Redis traffic")

        prune_task = asyncio.create_task(prune_loop())
        try:
            async for message in pubsub.listen():
                if message['type'] != 'pmessage':
                    continue

                channel = message['channel']
                if isinstance(channel, bytes):
                    channel = channel.decode('utf-8')

                data_str = message['data']
                if isinstance(data_str, bytes):
                    data_str = data_str.decode('utf-8')

                try:
                    data = json.loads(data_str)
                except json.JSONDecodeError as exc:
                    print_error(f"JSON parse failed: {exc}")
                    continue

                job_id = _extract_job_id(channel)
                if not job_id:
                    continue

                channel_type = channel.rsplit(':', 1)[-1]
                became_active = tracker.mark_seen(
                    job_id=job_id,
                    channel=channel,
                    message_type=channel_type,
                    payload=data,
                )
                current_connections = tracker.snapshot()

                if became_active:
                    print_connection_change("connect", job_id, current_connections.get(job_id, 1))
                elif last_connections.get(job_id) != current_connections.get(job_id):
                    if current_connections.get(job_id, 0) > last_connections.get(job_id, 0):
                        print_connection_change("connect", job_id, current_connections.get(job_id, 1))
                    else:
                        print_connection_change("disconnect", job_id, current_connections.get(job_id, 0))

                last_connections = current_connections
                print_redis_message(channel, data)
                print_websocket_push(
                    job_id,
                    {"type": channel_type, "timestamp": datetime.now().isoformat(), "data": data},
                    tracker.get_connection_count(),
                )
        finally:
            prune_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await prune_task
    except KeyboardInterrupt:
        print_info("monitor interrupted by user")
    except Exception as exc:
        print_error(f"monitor failed: {exc}")
    finally:
        await redis_client.close()
        print_info("Redis connection closed")


async def test_publish_message():
    print_header("test message publish")

    try:
        await redis_client.connect()
        test_job_id = "test-job-123"
        test_message = {
            "stage": "cad_parsing",
            "progress": 25,
            "message": "parsing CAD file...",
            "current_file": "test.dwg",
        }
        channel = f"job:{test_job_id}:progress"

        print_info(f"publishing test message to: {channel}")
        print_redis_message(channel, test_message)
        await redis_client.publish(channel, json.dumps(test_message, ensure_ascii=False))
        print_info("test message published")
    except Exception as exc:
        print_error(f"publish failed: {exc}")
    finally:
        await redis_client.close()


async def main():
    parser = argparse.ArgumentParser(description="Redis and WebSocket message monitor")
    parser.add_argument(
        "mode",
        choices=["redis", "websocket", "test"],
        help="monitor mode: redis=Redis messages, websocket=WebSocket activity, test=publish test message",
    )

    args = parser.parse_args()

    print(f"{Colors.BOLD}{Colors.HEADER}")
    print("=" * 80)
    print("Redis & WebSocket monitor".center(80))
    print("=" * 80)
    print(f"{Colors.ENDC}\n")

    print(f"{Colors.CYAN}config:{Colors.ENDC}")
    print(f"  Redis URL: {settings.REDIS_URL}")
    print(f"  mode: {args.mode}")
    print()

    if args.mode == "redis":
        await monitor_redis()
    elif args.mode == "websocket":
        await monitor_websocket_connections()
    elif args.mode == "test":
        await test_publish_message()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}program exited{Colors.ENDC}")
