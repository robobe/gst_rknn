#!/usr/bin/env python3
"""Small no-framework check for the benchmark command boundary."""
from protocol import PreviewCommand, Roi, RunCommand


def main():
    roi = Roi.from_json({"x": 1, "y": 2, "width": 3, "height": 4})
    assert roi.text() == "1,2,3,4"
    assert PreviewCommand.from_json({"source_path": "/home/radxa/a.mp4", "playback_fps": "Auto"}).playback_fps == "Auto"
    command = RunCommand.from_json({"source_path": "/home/radxa/a.mp4", "tracker_id": "v3-int8", "roi": roi.__dict__,
                                    "client_host": "10.0.0.2", "video_port": 5004, "metadata_port": 5005, "playback_fps": "30"})
    assert command.json()["roi"]["width"] == 3
    try:
        Roi.from_json({"x": 0, "y": 0, "width": 0, "height": 1})
    except ValueError:
        return
    raise AssertionError("invalid ROI accepted")


if __name__ == "__main__":
    main()
