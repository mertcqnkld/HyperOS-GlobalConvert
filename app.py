import os
import json
import queue
import threading
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from core.pipeline import run_patch_pipeline
from core.models import PipelineResult

app = FastAPI(title="GlobalConvertApps - APK Patcher Server")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "web", "static")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

class PatchRequest(BaseModel):
    url: str

@app.get("/", response_class=HTMLResponse)
async def read_index():
    index_file = os.path.join(STATIC_DIR, "index.html")
    if not os.path.exists(index_file):
        raise HTTPException(status_code=404, detail="index.html not found")
    with open(index_file, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

@app.post("/api/patch")
async def patch_apk_endpoint(req: PatchRequest):
    apk_url = req.url.strip()
    if not apk_url:
        raise HTTPException(status_code=400, detail="APK URL is required.")

    msg_queue = queue.Queue()

    def progress_handler(percentage: int, message: str, stage: str, data=None):
        msg_queue.put({
            "type": "progress",
            "percentage": percentage,
            "message": message,
            "stage": stage,
            "data": data
        })

    def run_worker():
        try:
            res: PipelineResult = run_patch_pipeline(
                apk_source=apk_url,
                output_dir=OUTPUT_DIR,
                progress_callback=progress_handler
            )
            if res.success:
                msg_queue.put({
                    "type": "complete",
                    "result": {
                        "success": True,
                        "output_filename": res.output_filename,
                        "file_size_bytes": res.file_size_bytes,
                        "total_dex_count": res.total_dex_count,
                        "total_patches": res.total_patches,
                        "patches": [
                            {
                                "class_name": p.class_name,
                                "method_name": p.method_name,
                                "line_number": p.line_number,
                                "opcode": p.opcode,
                                "register": p.register,
                                "original_line": p.original_line,
                                "injected_line": p.injected_line
                            }
                            for p in res.patches
                        ],
                        "skipped_count": len(res.skipped)
                    }
                })
            else:
                msg_queue.put({
                    "type": "error",
                    "message": res.error_message or "Unknown pipeline failure"
                })
        except Exception as ex:
            msg_queue.put({
                "type": "error",
                "message": str(ex)
            })
        finally:
            msg_queue.put(None)  # Sentinel to end stream

    threading.Thread(target=run_worker, daemon=True).start()

    def event_stream():
        while True:
            item = msg_queue.get()
            if item is None:
                break
            yield f"data: {json.dumps(item)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")

@app.get("/api/download")
async def download_patched_apk(file: str):
    safe_name = os.path.basename(file)
    target_path = os.path.join(OUTPUT_DIR, safe_name)
    if not os.path.exists(target_path):
        raise HTTPException(status_code=404, detail="Requested APK file does not exist.")
    return FileResponse(
        target_path,
        media_type="application/vnd.android.package-archive",
        filename=safe_name
    )

if __name__ == "__main__":
    print("=======================================================")
    print(" 🚀 GlobalConvertApps Web Server Running")
    print(" 🌐 Access UI at: http://127.0.0.1:8000")
    print("=======================================================")
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=False)
