#!/usr/bin/env python3
"""Print ROI UDP packet rate once per second."""

import argparse
import select
import socket
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=5005)
    args = parser.parse_args()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((args.host, args.port))
    print(f"Listening for ROI UDP on {args.host}:{args.port}", flush=True)
    total = 0
    last_total = 0
    started = last = time.monotonic()
    next_report = last + 1.0
    while True:
        readable, _, _ = select.select([sock], [], [], max(0, next_report - time.monotonic()))
        if readable:
            sock.recvfrom(65535)
            total += 1
        now = time.monotonic()
        if now >= next_report:
            elapsed = now - last
            print(f"packets={total} fps={(total - last_total) / elapsed:.1f} average={total / (now - started):.1f}", flush=True)
            last, last_total, next_report = now, total, now + 1.0


if __name__ == "__main__":
    main()
