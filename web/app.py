#!/usr/bin/env python3
"""
HyperOS-GlobalConvert Web Application Server
Zero-dependency embedded web server providing a modern UI for patching system APKs.
"""

import os
import sys
import json
import time
import uuid
import mimetypes
import threading
from urllib.parse import urlparse, parse_qs
from http.server import HTTPServer, BaseHTTPRequestHandler

# Add root directory to sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.pipeline import run_patch_pipeline
from core.models import PipelineResult

JOBS = {}
JOBS_LOCK = threading.Lock()
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

class WebRequestHandler(BaseHTTPRequestHandler):
    def _send_json(self, data, status_code=200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, filepath, content_type=None, filename=None):
        if not os.path.exists(filepath):
            self.send_error(404, "File not found")
            return

        if not content_type:
            content_type, _ = mimetypes.guess_type(filepath)
            content_type = content_type or "application/octet-stream"

        file_size = os.path.getsize(filepath)
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(file_size))
        if filename:
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.end_headers()

        with open(filepath, "rb") as f:
            while True:
                chunk = f.read(64 * 1024)
                if not chunk:
                    break
                self.wfile.write(chunk)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        # 1. Home Page
        if path == "/" or path == "/index.html":
            index_path = os.path.join(BASE_DIR, "web", "templates", "index.html")
            self._send_file(index_path, content_type="text/html; charset=utf-8")
            return

        # 2. Static Assets
        if path.startswith("/static/"):
            rel_path = path[len("/static/"):]
            asset_path = os.path.join(BASE_DIR, "web", "static", rel_path)
            self._send_file(asset_path)
            return

        # 3. Status API
        if path == "/api/status":
            job_id = query.get("job_id", [None])[0]
            if not job_id:
                self._send_json({"error": "Missing job_id"}, status_code=400)
                return

            with JOBS_LOCK:
                job = JOBS.get(job_id)

            if not job:
                self._send_json({"error": "Job not found"}, status_code=404)
                return

            self._send_json(job)
            return

        # 4. Download APK
        if path == "/api/download/apk":
            job_id = query.get("job_id", [None])[0]
            with JOBS_LOCK:
                job = JOBS.get(job_id)
            if not job or not job.get("apk_path") or not os.path.exists(job["apk_path"]):
                self.send_error(404, "Patched APK not ready or not found")
                return
            out_filename = job.get("output_filename") or os.path.basename(job["apk_path"])
            self._send_file(job["apk_path"], filename=out_filename)
            return

        # 5. Download Magisk Module
        if path == "/api/download/magisk":
            job_id = query.get("job_id", [None])[0]
            with JOBS_LOCK:
                job = JOBS.get(job_id)
            if not job or not job.get("magisk_zip_path") or not os.path.exists(job["magisk_zip_path"]):
                self.send_error(404, "Magisk zip not ready or not found")
                return
            magisk_fname = os.path.basename(job["magisk_zip_path"])
            self._send_file(job["magisk_zip_path"], filename=magisk_fname)
            return

        # 6. Download Report
        if path == "/api/download/report":
            job_id = query.get("job_id", [None])[0]
            with JOBS_LOCK:
                job = JOBS.get(job_id)
            if not job or not job.get("report_path") or not os.path.exists(job["report_path"]):
                self.send_error(404, "Report not found")
                return
            self._send_file(job["report_path"], content_type="application/json", filename=os.path.basename(job["report_path"]))
            return

        self.send_error(404, "Endpoint not found")

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/patch":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            try:
                data = json.loads(body)
            except Exception:
                self._send_json({"error": "Geçersiz JSON verisi"}, status_code=400)
                return

            url = data.get("url", "").strip()
            if not url:
                self._send_json({"error": "Lütfen geçerli bir APK URL'si veya dosya yolu girin."}, status_code=400)
                return

            job_id = str(uuid.uuid4())[:8]

            with JOBS_LOCK:
                JOBS[job_id] = {
                    "id": job_id,
                    "status": "queued",
                    "progress": 0,
                    "message": "İşlem sıraya alındı...",
                    "logs": [],
                    "patches": [],
                    "output_filename": None,
                    "file_size_bytes": 0,
                    "apk_path": None,
                    "magisk_zip_path": None,
                    "report_path": None,
                    "created_at": time.time()
                }

            # Start worker thread
            thread = threading.Thread(target=run_patch_job, args=(job_id, url), daemon=True)
            thread.start()

            self._send_json({"job_id": job_id, "status": "started"})
            return

        self.send_error(404, "Endpoint not found")

def run_patch_job(job_id: str, url: str):
    def update_callback(pct: int, msg: str, stage: str, data=None):
        with JOBS_LOCK:
            if job_id in JOBS:
                if pct >= 0:
                    JOBS[job_id]["progress"] = pct
                JOBS[job_id]["message"] = msg
                JOBS[job_id]["logs"].append(f"[{stage}] {msg}")

    with JOBS_LOCK:
        JOBS[job_id]["status"] = "running"
        JOBS[job_id]["progress"] = 5
        JOBS[job_id]["message"] = "APK analizi başlatılıyor..."

    result: PipelineResult = run_patch_pipeline(
        apk_source=url,
        output_dir=OUTPUT_DIR,
        progress_callback=update_callback
    )

    with JOBS_LOCK:
        if result.success:
            JOBS[job_id]["status"] = "completed"
            JOBS[job_id]["progress"] = 100
            JOBS[job_id]["message"] = "Patch işlemi başarıyla tamamlandı!"
            JOBS[job_id]["apk_path"] = result.output_apk_path
            JOBS[job_id]["output_filename"] = result.output_filename
            JOBS[job_id]["file_size_bytes"] = result.file_size_bytes
            JOBS[job_id]["magisk_zip_path"] = result.magisk_zip_path
            JOBS[job_id]["report_path"] = result.report_path
            JOBS[job_id]["patches"] = [
                {
                    "class_name": p.class_name,
                    "method_name": p.method_name,
                    "line_number": p.line_number,
                    "opcode": p.opcode,
                    "register": p.register,
                    "original_line": p.original_line,
                    "injected_line": p.injected_line
                }
                for p in result.patches
            ]
        else:
            JOBS[job_id]["status"] = "failed"
            JOBS[job_id]["progress"] = 0
            JOBS[job_id]["message"] = result.error_message or "İşlem sırasında beklenmeyen bir hata oluştu."

def start_server(port=8080):
    server = HTTPServer(("0.0.0.0", port), WebRequestHandler)
    print(f"""
===============================================================
   🌐 HyperOS GlobalConvert Web Arayüzü Başlatıldı 🌐
   Web UI Adresi: http://localhost:{port}
   Repository:    https://github.com/mertcqnkld/HyperOS-GlobalConvert
===============================================================
    """)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nWeb sunucu durduruldu.")
        server.server_close()

if __name__ == "__main__":
    port = 8080
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            pass
    start_server(port)
