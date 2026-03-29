"""Simple file server for Dormammu viewer.

Usage:
    python viewer/serve.py .dormammu/output
    python viewer/serve.py .dormammu/output --port 3000

Routes:
    GET /                → Home (simulation list)
    GET /sim/<sim-id>    → Viewer for specific simulation
    GET /api/sims        → JSON list of all simulations
    GET /data/<sim-id>/* → Data files for a simulation
"""
import http.server
import json
import os
import sys
from pathlib import Path


viewer_dir = Path(__file__).parent.resolve()


class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            self._serve_file(viewer_dir / "index.html", "text/html; charset=utf-8")

        elif self.path.startswith("/sim/"):
            # SPA-style: always serve index.html, JS handles routing
            self._serve_file(viewer_dir / "index.html", "text/html; charset=utf-8")

        elif self.path == "/api/sims":
            self._serve_sims_list()

        elif self.path.startswith("/api/characters/"):
            sim_id = self.path[len("/api/characters/"):]
            self._serve_characters_list(sim_id)

        elif self.path.startswith("/api/images/"):
            # /api/images/<sim-id>/<node-path> → list images in node's images/ folder
            rel = self.path[len("/api/images/"):]
            parts = rel.split("/", 1)
            if len(parts) == 2:
                sim_id, node_path = parts
                self._serve_node_images_list(sim_id, node_path)
            else:
                self.send_error(404)

        elif self.path.startswith("/data/"):
            # /data/<sim-id>/path/to/file
            rel = self.path[len("/data/"):]
            target = (output_dir / rel).resolve()
            if not target.is_relative_to(output_dir):
                self.send_error(403)
                return
            # Fallback: run-state.json in .dormammu/ root
            if not target.exists() and rel.endswith("run-state.json"):
                fallback = (output_dir.parent / "run-state.json").resolve()
                if not fallback.is_relative_to(output_dir.parent):
                    self.send_error(403)
                    return
                target = fallback
            self._serve_file(target, None)

        else:
            self.send_error(404)

    def _serve_sims_list(self):
        """Return JSON array of simulation summaries."""
        sims = []
        if output_dir.exists():
            for d in sorted(output_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
                if not d.is_dir():
                    continue
                idx_path = d / "tree-index.json"
                entry = {"sim_id": d.name, "path": d.name}
                if idx_path.exists():
                    try:
                        idx = json.loads(idx_path.read_text(encoding="utf-8"))
                        entry["topic"] = idx.get("topic", "")
                        entry["node_count"] = len(idx.get("nodes", {}))
                        entry["best_path"] = idx.get("best_path", [])
                        # Find best score
                        nodes = idx.get("nodes", {})
                        scores = [n.get("composite_score") for n in nodes.values() if n.get("composite_score") is not None]
                        entry["best_score"] = max(scores) if scores else None
                        entry["max_depth"] = max((n.get("depth", 0) for n in nodes.values()), default=0)
                        # Aggregate stats
                        entry["total_duration"] = sum(n.get("duration_sec", 0) for n in nodes.values())
                        entry["total_chars"] = sum(n.get("chars", 0) for n in nodes.values())
                        entry["total_cost"] = round(sum(float(n.get("cost", 0)) for n in nodes.values()), 4)
                    except (json.JSONDecodeError, KeyError):
                        pass
                # Check run-state.json
                rs_path = d / "run-state.json"
                if not rs_path.exists():
                    rs_path = output_dir.parent / "run-state.json"
                if rs_path.exists():
                    try:
                        rs = json.loads(rs_path.read_text(encoding="utf-8"))
                        if rs.get("sim_id") == d.name:
                            entry["phase"] = rs.get("phase", "unknown")
                            entry["started_at"] = rs.get("started_at")
                            entry["updated_at"] = rs.get("updated_at")
                            entry["nodes_completed"] = rs.get("nodes_completed")
                    except (json.JSONDecodeError, KeyError):
                        pass
                sims.append(entry)

        data = json.dumps(sims, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(data)

    def _serve_characters_list(self, sim_id):
        """Return JSON array of character filenames for a simulation."""
        chars_dir = (output_dir / sim_id / "characters").resolve()
        if not chars_dir.is_relative_to(output_dir):
            self.send_error(403)
            return
        files = []
        if chars_dir.is_dir():
            for f in sorted(chars_dir.iterdir()):
                if f.suffix == ".md" and f.is_file():
                    files.append(f.name)
        data = json.dumps(files, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(data)

    def _serve_node_images_list(self, sim_id, node_path):
        """Return JSON array of image filenames in a node's images/ folder."""
        images_dir = (output_dir / sim_id / node_path / "images").resolve()
        if not images_dir.is_relative_to(output_dir):
            self.send_error(403)
            return
        files = []
        if images_dir.is_dir():
            for f in sorted(images_dir.iterdir()):
                if f.is_file() and f.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp", ".gif"):
                    files.append(f.name)
        data = json.dumps(files, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(data)

    _MIME = {
        ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".webp": "image/webp", ".gif": "image/gif", ".svg": "image/svg+xml",
    }

    def _serve_file(self, path: Path, content_type):
        try:
            data = path.read_bytes()
        except (FileNotFoundError, IsADirectoryError):
            self.send_error(404)
            return
        if content_type is None:
            if path.suffix == ".json":
                content_type = "application/json; charset=utf-8"
            elif path.suffix == ".md":
                content_type = "text/plain; charset=utf-8"
            elif path.suffix.lower() in self._MIME:
                content_type = self._MIME[path.suffix.lower()]
            else:
                content_type = "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt, *args):
        pass  # suppress per-request logs


PORT = int(os.environ.get("PORT", 3000))

if len(sys.argv) < 2:
    print("Usage: python viewer/serve.py .dormammu/output")
    sys.exit(1)

output_dir = Path(sys.argv[1]).resolve()

if not output_dir.exists():
    print(f"ERROR: directory not found: {output_dir}")
    sys.exit(1)

print(f"Output   : {output_dir}")
print(f"Viewer   : {viewer_dir}/index.html")
print(f"Open     : http://localhost:{PORT}/")
print("Ctrl+C to stop.")
http.server.HTTPServer(("", PORT), Handler).serve_forever()
