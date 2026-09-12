#!/usr/bin/env python3
"""Desktop client for the Radxa NanoTracker benchmark service."""
import argparse
import json
import socket
import threading
import time
import tkinter as tk
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from tkinter import messagebox, ttk

import cv2
import gi
import numpy as np
import yaml

gi.require_version("Gst", "1.0")
gi.require_version("GstVideo", "1.0")
from gi.repository import Gst, GstVideo


class Api:
    def __init__(self, base): self.base = base.rstrip("/")

    def request(self, method, path, payload=None, binary=False, timeout=10):
        data = json.dumps(payload).encode() if payload is not None else None
        request = urllib.request.Request(self.base + path, data=data, method=method)
        if data: request.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                data = response.read()
                return data if binary else json.loads(data)
        except urllib.error.HTTPError as error:
            raise RuntimeError(error.read().decode() or error.reason) from error
        except urllib.error.URLError as error:
            raise RuntimeError(str(error.reason)) from error


class StreamViewer:
    def __init__(self, video_port, metadata_port):
        self.video_port, self.metadata_port = video_port, metadata_port
        self.box, self.stop_event, self.thread = None, threading.Event(), None
        self.pipeline = self.sink = None
        self.frames, self.first_frame, self.last_frame = 0, None, None

    def start(self):
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._metadata, daemon=True)
        self.thread.start()
        self.pipeline = Gst.parse_launch(
            f'udpsrc port={self.video_port} caps="application/x-rtp,media=video,encoding-name=JPEG,payload=26,clock-rate=90000" ! '
            'rtpjitterbuffer latency=200 drop-on-latency=false ! rtpjpegdepay ! jpegdec ! '
            'videoconvert ! video/x-raw,format=BGR ! appsink name=sink sync=false max-buffers=1 drop=true'
        )
        self.sink = self.pipeline.get_by_name("sink")
        self.pipeline.set_state(Gst.State.PLAYING)

    def _metadata(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.bind(("0.0.0.0", self.metadata_port)); sock.settimeout(0.25)
            while not self.stop_event.is_set():
                try:
                    fields = sock.recvfrom(2048)[0].decode().strip().split(",")
                    if len(fields) >= 8:
                        self.box = (fields[1], *(int(value) for value in fields[2:6]), fields[6], fields[7])
                except (socket.timeout, UnicodeDecodeError, ValueError):
                    pass
        finally:
            sock.close()

    def poll(self):
        if not self.sink: return
        sample = self.sink.emit("try-pull-sample", 0)
        if sample is None: return
        caps = sample.get_caps().get_structure(0)
        ok_w, width = caps.get_int("width"); ok_h, height = caps.get_int("height")
        if not ok_w or not ok_h: return
        buffer = sample.get_buffer(); meta = GstVideo.buffer_get_video_meta(buffer)
        ok, mapped = buffer.map(Gst.MapFlags.READ)
        if not ok: return
        try:
            stride = meta.stride[0] if meta else width * 3
            frame = np.ndarray((height, width, 3), dtype=np.uint8, buffer=mapped.data, strides=(stride, 3, 1)).copy()
        finally:
            buffer.unmap(mapped)
        now = time.monotonic(); self.first_frame = self.first_frame or now
        self.last_frame, self.frames = now, self.frames + 1
        if self.box:
            name, x, y, w, h, initialized, confidence = self.box
            color = (0, 255, 255) if initialized == "1" else (0, 0, 255) if confidence and float(confidence) < .5 else (0, 255, 0)
            cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
            cv2.putText(frame, f"{name} {confidence or 'init'}", (x, max(18, y - 5)), cv2.FONT_HERSHEY_SIMPLEX, .55, color, 2)
        elapsed = max(now - self.first_frame, 1e-9)
        cv2.putText(frame, f"client FPS: {self.frames / elapsed:.1f}", (12, 28), cv2.FONT_HERSHEY_SIMPLEX, .75, (0, 255, 0), 2)
        cv2.imshow("NanoTracker benchmark", frame); cv2.waitKey(1)

    def metrics(self):
        return {"frames": self.frames, "elapsed_s": max((self.last_frame or 0) - (self.first_frame or 0), 1e-9)}

    def close(self):
        self.stop_event.set()
        if self.pipeline: self.pipeline.set_state(Gst.State.NULL)
        self.pipeline = self.sink = None
        cv2.destroyAllWindows()


class Client:
    def __init__(self, config_path):
        config = yaml.safe_load(Path(config_path).read_text()) or {}
        self.api, self.client_host = Api(config["server_url"]), config["client_host"]
        self.video_port, self.metadata_port = int(config["video_port"]), int(config["metadata_port"])
        self.state_path = Path.home() / ".config" / "gst-rknn" / "nanotracker-benchmark-last-run.yaml"
        Gst.init(None); self.catalog = {}; self.viewer = self.run_id = self.roi = self.terminal_at = None; self.last_run_id = None
        self.next_server_check = self.next_run_check = 0.0
        self.root = tk.Tk(); self.root.title("NanoTracker benchmark"); self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.source, self.ground_truth = tk.StringVar(), tk.StringVar()
        self.dataset, self.tracker, self.rate = tk.StringVar(value="Ad-hoc source"), tk.StringVar(), tk.StringVar(value="Auto")
        self.saved_run, self.preset_name = tk.StringVar(), tk.StringVar()
        self.saved_items = {}
        self.server_status, self.status = tk.StringVar(value="Server: connecting"), tk.StringVar(value="Connecting to benchmark server")
        self._build(); self._load_catalog(); self.root.after(30, self.tick)

    def _build(self):
        panel = ttk.Frame(self.root, padding=12); panel.grid(sticky="nsew")
        connection = ttk.Frame(panel); connection.grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 8))
        self.server_led = tk.Canvas(connection, width=14, height=14, highlightthickness=0)
        self.server_led.pack(side="left", padx=(0, 4)); self.led_item = self.server_led.create_oval(2, 2, 12, 12, fill="#c62828", outline="")
        ttk.Label(connection, textvariable=self.server_status).pack(side="left")
        ttk.Label(panel, text="Recent / preset").grid(row=1, column=0, sticky="nw", pady=3)
        saved_frame = ttk.Frame(panel); saved_frame.grid(row=1, column=1, rowspan=2, sticky="nsew", pady=3)
        self.saved_run_list = tk.Listbox(saved_frame, height=5, exportselection=False)
        saved_scroll = ttk.Scrollbar(saved_frame, orient="vertical", command=self.saved_run_list.yview)
        self.saved_run_list.configure(yscrollcommand=saved_scroll.set)
        self.saved_run_list.pack(side="left", fill="both", expand=True); saved_scroll.pack(side="right", fill="y")
        self.saved_run_list.bind("<<ListboxSelect>>", lambda _: self.load_saved_run())
        preset_actions = ttk.Frame(panel); preset_actions.grid(row=1, column=2, padx=(6, 0))
        ttk.Button(preset_actions, text="Save", command=self.save_preset).pack(side="top", fill="x")
        ttk.Button(preset_actions, text="Rename", command=self.rename_preset).pack(side="top", fill="x", pady=(3, 0))
        ttk.Label(panel, text="Preset name").grid(row=3, column=0, sticky="w", pady=3)
        ttk.Entry(panel, textvariable=self.preset_name, width=52).grid(row=3, column=1, sticky="ew", pady=3)
        for row, label in enumerate(("Dataset", "Source", "Ground truth", "Tracker", "Playback FPS"), start=4):
            ttk.Label(panel, text=label).grid(row=row, column=0, sticky="w", pady=3)
        self.dataset_box = ttk.Combobox(panel, textvariable=self.dataset, state="readonly", width=52); self.dataset_box.grid(row=4, column=1, sticky="ew", pady=3); self.dataset_box.bind("<<ComboboxSelected>>", lambda _: self.choose_dataset())
        ttk.Entry(panel, textvariable=self.source, width=52).grid(row=5, column=1, sticky="ew", pady=3); ttk.Button(panel, text="Browse", command=self.browse).grid(row=5, column=2, padx=(6, 0))
        ttk.Entry(panel, textvariable=self.ground_truth, width=52).grid(row=6, column=1, sticky="ew", pady=3); ttk.Button(panel, text="Browse", command=lambda: self.browse(ground_truth=True)).grid(row=6, column=2, padx=(6, 0))
        self.tracker_box = ttk.Combobox(panel, textvariable=self.tracker, state="readonly", width=52); self.tracker_box.grid(row=7, column=1, sticky="ew", pady=3)
        ttk.Combobox(panel, textvariable=self.rate, values=("Auto", "1", "5", "10", "20", "30"), state="readonly", width=52).grid(row=8, column=1, sticky="ew", pady=3)
        ttk.Button(panel, text="Preview / select ROI", command=self.preview).grid(row=9, column=0, sticky="ew", pady=(8, 3)); ttk.Button(panel, text="Play source", command=lambda: self.start(source_only=True)).grid(row=9, column=1, sticky="ew", padx=(6, 0), pady=(8, 3)); ttk.Button(panel, text="Start benchmark", command=self.start).grid(row=9, column=2, sticky="ew", padx=(6, 0), pady=(8, 3))
        ttk.Button(panel, text="Show pipeline", command=self.show_pipeline).grid(row=10, column=1, sticky="ew", pady=3)
        ttk.Button(panel, text="Stop", command=self.stop).grid(row=10, column=2, sticky="ew", padx=(6, 0), pady=3)
        ttk.Label(panel, textvariable=self.status, wraplength=620, justify="left").grid(row=11, column=0, columnspan=3, sticky="ew", pady=(8, 0))
        panel.columnconfigure(1, weight=1)

    def set_server_connected(self, connected):
        self.server_led.itemconfigure(self.led_item, fill="#249447" if connected else "#c62828")
        self.server_status.set("Server: connected" if connected else "Server: unavailable")

    def _load_catalog(self):
        try:
            self.catalog = self.api.request("GET", "/v1/catalog")
            self.dataset_box.configure(values=["Ad-hoc source", *self.catalog["datasets"]])
            self.tracker_labels = {item["label"]: item["id"] for item in self.catalog["trackers"]}
            self.tracker_box.configure(values=list(self.tracker_labels)); self.tracker.set(next(iter(self.tracker_labels)))
            self.load_last_selection()
            self.refresh_saved_runs()
            self.set_server_connected(True)
            self.status.set("Choose a dataset or browse a Radxa source")
        except RuntimeError as error:
            self.set_server_connected(False); self.status.set(f"Server unavailable: {error}")

    def state_document(self):
        try:
            state = yaml.safe_load(self.state_path.read_text()) or {}
        except (OSError, yaml.YAMLError):
            return {"recent_runs": [], "presets": {}}
        if not isinstance(state, dict):
            return {"recent_runs": [], "presets": {}}
        if "last_run" not in state and "source_path" in state:
            state = {"last_run": state, "recent_runs": [state], "presets": {}}
        state.setdefault("recent_runs", []); state.setdefault("presets", {})
        return state

    def write_state(self, state):
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(yaml.safe_dump(state, sort_keys=False))

    def apply_selection(self, state):
        self.roi = None
        for variable, key in ((self.source, "source_path"), (self.ground_truth, "ground_truth"), (self.rate, "playback_fps")):
            if isinstance(state.get(key), str):
                variable.set(state[key])
        for label, tracker_id in self.tracker_labels.items():
            if tracker_id == state.get("tracker_id"):
                self.tracker.set(label)
                break
        if state.get("dataset") in self.dataset_box["values"]:
            self.dataset.set(state["dataset"])
        roi = state.get("roi")
        if state.get("roi_size") == [640, 360] and isinstance(roi, dict) and all(isinstance(roi.get(key), int) for key in ("x", "y", "width", "height")):
            self.roi = roi

    def load_last_selection(self):
        state = self.state_document().get("last_run")
        if isinstance(state, dict): self.apply_selection(state)

    def selection(self, payload=None):
        payload = payload or {"tracker_id": self.tracker_labels.get(self.tracker.get(), ""), "roi": self.roi,
                              "playback_fps": self.rate.get(), "ground_truth": self.ground_truth.get() or None,
                              "source_path": self.source.get(), "client_host": self.client_host,
                              "video_port": self.video_port, "metadata_port": self.metadata_port}
        return {"dataset": self.dataset.get(), "source_path": payload["source_path"], "ground_truth": payload["ground_truth"] or "",
                "tracker_id": payload["tracker_id"], "playback_fps": payload["playback_fps"], "roi": payload["roi"], "roi_size": [640, 360],
                "client_host": payload["client_host"], "video_port": payload["video_port"], "metadata_port": payload["metadata_port"],
                "source_only": payload["tracker_id"] == "source", "saved_at": time.strftime("%Y-%m-%d %H:%M:%S")}

    def save_last_selection(self, payload):
        state, run = self.state_document(), self.selection(payload)
        state["last_run"] = run; state["recent_runs"] = [run, *state["recent_runs"]][:10]
        self.write_state(state); self.refresh_saved_runs(state)

    def refresh_saved_runs(self, state=None):
        state = state or self.state_document(); self.saved_items = {}
        for index, run in enumerate(state["recent_runs"]):
            if isinstance(run, dict):
                label = f"Recent: {run.get('saved_at', '?')} | {Path(run.get('source_path', '?')).name}"
                self.saved_items[f"{label} #{index + 1}"] = run
        for name, run in state["presets"].items():
            if isinstance(name, str) and isinstance(run, dict): self.saved_items[f"Preset: {name}"] = run
        self.saved_run_list.delete(0, tk.END)
        for label in self.saved_items: self.saved_run_list.insert(tk.END, label)

    def load_saved_run(self):
        choice = self.saved_run_list.curselection()
        if not choice: return
        self.saved_run.set(self.saved_run_list.get(choice[0]))
        run = self.saved_items.get(self.saved_run.get())
        if run:
            self.apply_selection(run)
            if self.saved_run.get().startswith("Preset: "): self.preset_name.set(self.saved_run.get()[8:])
            self.status.set("Saved run loaded; preview again if you change the source")

    def save_preset(self):
        name = self.preset_name.get().strip()
        if not name: self.status.set("Enter a preset name first"); return
        state = self.state_document(); state["presets"][name] = self.selection()
        self.write_state(state); self.refresh_saved_runs(state); self.saved_run.set(f"Preset: {name}")
        self.status.set(f"Preset saved: {name}")

    def rename_preset(self):
        selected, name = self.saved_run.get(), self.preset_name.get().strip()
        if not selected.startswith("Preset: ") or not name: self.status.set("Select a preset and enter its new name"); return
        old = selected[8:]
        if old == name: return
        state = self.state_document()
        if name in state["presets"]: self.status.set("That preset name already exists"); return
        state["presets"][name] = state["presets"].pop(old); self.write_state(state); self.refresh_saved_runs(state)
        self.saved_run.set(f"Preset: {name}"); self.status.set(f"Preset renamed: {name}")

    def choose_dataset(self):
        item = self.catalog["datasets"].get(self.dataset.get())
        if not item: return
        self.source.set(item["source_path"]); self.ground_truth.set(item.get("ground_truth") or ""); self.rate.set(item.get("playback_fps", "Auto"))
        roi = item.get("initial_roi"); self.roi = dict(zip(("x", "y", "width", "height"), roi)) if roi else None
        self.status.set("Dataset loaded; preview to keep or replace its ROI")

    def browse(self, ground_truth=False):
        chooser = tk.Toplevel(self.root); chooser.title("Select ground truth on Radxa" if ground_truth else "Browse Radxa /home/radxa")
        path, entries = tk.StringVar(value="/home/radxa/gst-rknn/datasets"), tk.Listbox(chooser, width=80, height=20)
        ttk.Entry(chooser, textvariable=path, width=72).pack(padx=8, pady=5); entries.pack(fill="both", expand=True, padx=8, pady=5)
        def refresh(directory=None):
            try:
                data = self.api.request("GET", "/v1/browse?path=" + urllib.parse.quote(directory or path.get()))
                path.set(data["path"]); entries.delete(0, tk.END); entries.insert(tk.END, ".."); chooser.items = data["entries"]
                for item in chooser.items: entries.insert(tk.END, ("[D] " if item["directory"] else "[F] ") + item["name"])
            except RuntimeError as error: messagebox.showerror("Browse failed", str(error), parent=chooser)
        def select(_event=None):
            choice = entries.curselection()
            if not choice: return
            if choice[0] == 0: refresh(str(Path(path.get()).parent)); return
            item = chooser.items[choice[0] - 1]
            if item["directory"]: refresh(item["path"])
            else:
                if ground_truth:
                    self.ground_truth.set(item["path"])
                else:
                    self.source.set(item["path"]); self.dataset.set("Ad-hoc source"); self.ground_truth.set(""); self.roi = None
                chooser.destroy()
        def use_folder():
            self.source.set(path.get()); self.dataset.set("Ad-hoc source"); self.ground_truth.set(""); self.roi = None; chooser.destroy()
        ttk.Button(chooser, text="Refresh", command=refresh).pack(side="left", padx=8, pady=5)
        if not ground_truth: ttk.Button(chooser, text="Use this folder", command=use_folder).pack(side="left", padx=8, pady=5)
        entries.bind("<Double-Button-1>", select); refresh()

    def preview(self):
        try:
            reply = self.api.request("POST", "/v1/previews", {"source_path": self.source.get(), "playback_fps": self.rate.get()})
            frame = cv2.imdecode(np.frombuffer(self.api.request("GET", reply["url"], binary=True), dtype=np.uint8), cv2.IMREAD_COLOR)
            frame = cv2.resize(frame, (640, 360), interpolation=cv2.INTER_AREA)
            selected = cv2.selectROI("Select tracker ROI", frame, showCrosshair=True, fromCenter=False); cv2.destroyWindow("Select tracker ROI")
            if selected[2] > 0 and selected[3] > 0:
                self.roi = dict(zip(("x", "y", "width", "height"), map(int, selected))); self.status.set(f"ROI selected: {self.roi}")
            elif self.roi: self.status.set("ROI selection cancelled; keeping dataset ROI")
        except RuntimeError as error: self.status.set(f"Preview failed: {error}")

    def start(self, source_only=False):
        if not source_only and not self.roi: self.status.set("Preview and select an ROI first"); return
        payload = {"source_path": self.source.get(), "ground_truth": None if source_only else self.ground_truth.get() or None,
                   "tracker_id": "source" if source_only else self.tracker_labels.get(self.tracker.get(), ""),
                   "roi": self.roi or {"x": 0, "y": 0, "width": 1, "height": 1}, "client_host": self.client_host,
                   "video_port": self.video_port, "metadata_port": self.metadata_port, "playback_fps": self.rate.get()}
        try:
            self.viewer = StreamViewer(self.video_port, self.metadata_port); self.viewer.start()
            self.run_id = self.api.request("POST", "/v1/runs", payload)["id"]; self.last_run_id = self.run_id; self.status.set(f"Playing {self.run_id}" if source_only else f"Running {self.run_id}")
            self.save_last_selection(payload)
        except RuntimeError as error:
            if self.viewer: self.viewer.close(); self.viewer = None
            self.status.set(f"Start failed: {error}")

    def stop(self):
        if self.run_id:
            try: self.api.request("POST", f"/v1/runs/{self.run_id}/stop")
            except RuntimeError as error: self.status.set(f"Stop failed: {error}")

    def show_pipeline(self):
        run_id = self.run_id or self.last_run_id
        if not run_id:
            self.status.set("Start a run first")
            return
        try:
            pipeline = self.api.request("GET", f"/v1/runs/{run_id}").get("pipeline")
        except RuntimeError as error:
            self.status.set(f"Pipeline unavailable: {error}")
            return
        if not pipeline:
            self.status.set("Pipeline is not ready yet")
            return
        window = tk.Toplevel(self.root); window.title(f"Pipeline: {run_id}")
        text = tk.Text(window, width=108, height=8, wrap="word"); text.pack(fill="both", expand=True, padx=8, pady=8)
        text.insert("1.0", pipeline); text.configure(state="disabled")

    def tick(self):
        now = time.monotonic()
        if self.viewer: self.viewer.poll()
        if not self.run_id and now >= self.next_server_check:
            self.next_server_check = now + 2
            try:
                self.api.request("GET", "/v1/health", timeout=1.5)
                self.set_server_connected(True)
            except RuntimeError:
                self.set_server_connected(False)
        if self.run_id and now >= self.next_run_check:
            self.next_run_check = now + .5
            try:
                result = self.api.request("GET", f"/v1/runs/{self.run_id}")
                self.set_server_connected(True)
                if result["status"] in ("finished", "failed", "stopped"):
                    self.terminal_at = self.terminal_at or time.monotonic()
                    if time.monotonic() - self.terminal_at >= .75:
                        self.api.request("POST", f"/v1/runs/{self.run_id}/client-metrics", self.viewer.metrics() if self.viewer else {"frames": 0, "elapsed_s": 1.0})
                        if self.viewer: self.viewer.close(); self.viewer = None
                        self.status.set(f"{result['status']}: artifacts ready under {self.run_id}"); self.run_id = self.terminal_at = None
            except RuntimeError as error:
                self.set_server_connected(False); self.status.set(f"Status failed: {error}")
        self.root.after(30, self.tick)

    def close(self):
        self.stop()
        if self.viewer: self.viewer.close()
        self.root.destroy()

    def run(self): self.root.mainloop()


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--config", type=Path, default=Path(__file__).with_name("client.yaml"))
    Client(parser.parse_args().config).run()


if __name__ == "__main__": main()
