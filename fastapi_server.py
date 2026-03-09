import os
from pathlib import Path
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import subprocess
import logging
from typing import Optional

# Setup basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Groww Pulse Analyser API")

# Allow the Next.js frontend to talk to this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict this to your Vercel URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class PipelineRequest(BaseModel):
    weeks: int = 8
    topics: Optional[str] = ""
    email: Optional[str] = ""
    send: bool = False

@app.get("/health")
def health_check():
    return {"status": "ok", "message": "Groww Pulse Analyser Backend is running."}

@app.post("/api/run-pipeline")
async def run_pipeline(request: PipelineRequest, background_tasks: BackgroundTasks):
    """
    Executes the main.py pipeline synchronously and returns the output logs.
    Warning: This endpoint can take 30-60 seconds depending on Gemini/Groq APIs.
    """
    logger.info(f"Incoming request: weeks={request.weeks}, topics='{request.topics}', send={request.send}")
    
    # We will simply call the existing main.py CLI so we don't have to rewrite the orchestration logic
    args = ["python", "main.py", "--phase", "all", "--weeks", str(request.weeks)]
    
    if request.topics:
        args.extend(["--topics", str(request.topics)])
    if request.send:
        args.append("--send")
        
    env = os.environ.copy()
    if request.email:
        env["EMAIL_TO"] = str(request.email)
        
    try:
        # Run the process
        # Using subprocess.run ensures we block and wait for the pipeline to finish 
        # before returning the logs to the Next.js UI
        process = subprocess.run(
            args, 
            capture_output=True, 
            text=True, 
            check=True,
            env=env
        )
        
        return {
            "status": "ok",
            "stdout": process.stdout,
            "stderr": process.stderr
        }
    except subprocess.CalledProcessError as e:
        logger.error(f"Pipeline failed: {e.stderr}")
        raise HTTPException(
            status_code=500, 
            detail={
                "message": "Pipeline execution failed",
                "stdout": e.stdout,
                "stderr": e.stderr
            }
        )

# Added simple GET endpoint for the UI to retrieve the latest pulse Markdown
@app.get("/api/pulse")
def get_latest_pulse():
    pulse_dir = Path("data/pulse")
    if not pulse_dir.exists():
        return {"pulse": None, "filename": None}
        
    md_files = list(pulse_dir.glob("pulse-*.md"))
    if not md_files:
        return {"pulse": None, "filename": None}
        
    # Sort files by modification time, descending
    md_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    latest_file = md_files[0]
    
    return {
        "pulse": latest_file.read_text(encoding="utf-8"),
        "filename": latest_file.name
    }

if __name__ == "__main__":
    import uvicorn
    # When deployed on platforms like Render, port is provided via the PORT environment variable
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("fastapi_server:app", host="0.0.0.0", port=port, reload=True)
