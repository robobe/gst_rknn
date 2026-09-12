#!/usr/bin/env python3
"""Display RTP/H.264 video and draw ROI CSV datagrams with Cairo."""

import argparse
import socket
import threading

import gi

gi.require_version("Gst", "1.0")
from gi.repository import GLib, Gst


class Viewer:
    def __init__(self, metadata_port):
        self.box = None
        self.lock = threading.Lock()
        self.stop = threading.Event()
        self.metadata_port = metadata_port

    def receive_metadata(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(("0.0.0.0", self.metadata_port))
        sock.settimeout(0.5)
        while not self.stop.is_set():
            try:
                fields = sock.recvfrom(2048)[0].decode().strip().split(",")
                if len(fields) >= 6:
                    with self.lock:
                        self.box = fields[1], *(int(value) for value in fields[2:6])
            except socket.timeout:
                pass
            except (UnicodeDecodeError, ValueError):
                pass
        sock.close()

    def draw(self, _overlay, context, _timestamp, _duration):
        with self.lock:
            box = self.box
        if not box:
            return
        name, x, y, width, height = box
        context.set_source_rgb(1, 0.1, 0.1)
        context.set_line_width(3)
        context.rectangle(x, y, width, height)
        context.stroke()
        context.set_font_size(16)
        context.move_to(x, max(18, y - 5))
        context.show_text(name)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video-port", type=int, default=5004)
    parser.add_argument("--metadata-port", type=int, default=5005)
    args = parser.parse_args()

    Gst.init(None)
    viewer = Viewer(args.metadata_port)
    threading.Thread(target=viewer.receive_metadata, daemon=True).start()
    pipeline = Gst.parse_launch(
        f'udpsrc port={args.video_port} caps="application/x-rtp,media=video,encoding-name=H264,payload=96,clock-rate=90000" ! '
        'rtpjitterbuffer latency=200 drop-on-latency=false ! rtph264depay ! h264parse ! avdec_h264 ! '
        'videoconvert ! video/x-raw,format=BGRA ! cairooverlay name=overlay ! videoconvert ! '
        'fpsdisplaysink video-sink=autovideosink text-overlay=true sync=false'
    )
    overlay = pipeline.get_by_name("overlay")
    overlay.connect("draw", viewer.draw)
    loop = GLib.MainLoop()
    bus = pipeline.get_bus()
    bus.add_signal_watch()
    bus.connect("message::error", lambda _bus, message: (print(message.parse_error()[0]), loop.quit()))
    print(f"Video UDP {args.video_port}; ROI UDP {args.metadata_port}. Press Ctrl+C to stop.", flush=True)
    pipeline.set_state(Gst.State.PLAYING)
    try:
        loop.run()
    except KeyboardInterrupt:
        pass
    finally:
        viewer.stop.set()
        pipeline.set_state(Gst.State.NULL)


if __name__ == "__main__":
    main()
