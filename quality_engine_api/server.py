from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, Request, Depends
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from starlette.middleware.base import BaseHTTPMiddleware
import uuid
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import os  # ← THIS WAS MISSING!
import re
import secrets
import logging
from collections import defaultdict
from dotenv import load_dotenv  # ← ADD THIS

# Load environment variables
load_dotenv()  # ← ADD THIS

# ============================================================================
# LOGGING SETUP
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# INITIALIZATION
# ============================================================================

app = FastAPI(title="PamojaData Quality Engine", version="1.0.0")

# Rate limiting storage
rate_limits = defaultdict(list)
jobs = {}

# API Key Setup - NOW READS FROM .env FIRST
API_KEY = os.getenv("QUALITY_API_KEY")
if not API_KEY:
    # If no key in .env, generate one and save it
    API_KEY = secrets.token_urlsafe(32)
    # Save to .env for next time
    with open(".env", "a") as f:
        f.write(f"\nQUALITY_API_KEY={API_KEY}\n")
    logger.info(f"Generated new API Key and saved to .env")

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# Rate limit configuration
RATE_LIMIT = {
    'api': {'max_attempts': 100, 'window_minutes': 1},
    'upload': {'max_attempts': 10, 'window_minutes': 5},
    'auth': {'max_attempts': 5, 'window_minutes': 15}
}

# ============================================================================
# SECURITY FUNCTIONS
# ============================================================================

def rate_limit_check(client_ip: str, endpoint_type: str) -> bool:
    """Check if request exceeds rate limit"""
    now = datetime.now()
    config = RATE_LIMIT.get(endpoint_type, RATE_LIMIT['api'])
    window = timedelta(minutes=config['window_minutes'])
    
    # Clean old entries
    rate_limits[client_ip] = [ts for ts in rate_limits[client_ip] if now - ts < window]
    
    if len(rate_limits[client_ip]) >= config['max_attempts']:
        return False
    
    rate_limits[client_ip].append(now)
    return True

def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent path traversal"""
    if not filename:
        return "unknown_file"
    # Remove path traversal attempts
    filename = re.sub(r'\.\./', '', filename)
    filename = re.sub(r'\.\.\\', '', filename)
    # Remove any null bytes
    filename = filename.replace('\x00', '')
    # Allow only alphanumeric, dot, dash, underscore
    filename = re.sub(r'[^a-zA-Z0-9_.-]', '_', filename)
    # Limit length
    return filename[:255]

def validate_file_size(content: bytes, max_mb: int = 50) -> bool:
    """Validate file size is within limits"""
    return len(content) <= max_mb * 1024 * 1024

# ============================================================================
# MIDDLEWARE
# ============================================================================

class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Middleware to limit request size"""
    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > 50 * 1024 * 1024:  # 50MB
            logger.warning(f"Request too large: {content_length} bytes from {request.client.host}")
            return JSONResponse(
                status_code=413, 
                content={"error": "Request too large. Max 50MB."}
            )
        return await call_next(request)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501", "http://localhost:8502", "http://127.0.0.1:8501"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["X-Requested-With", "Content-Type", "Authorization", "X-API-Key"],
    max_age=3600,
)

# Add request size limit middleware
app.add_middleware(RequestSizeLimitMiddleware)

# API Key authentication middleware
@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    """Global authentication middleware"""
    # Skip auth for public endpoints
    public_paths = ["/", "/health", "/docs", "/openapi.json", "/redoc"]
    if request.url.path in public_paths:
        return await call_next(request)
    
    # Check API key for all other endpoints
    api_key = request.headers.get("X-API-Key")
    if not API_KEY or api_key != API_KEY:
        logger.warning(f"Invalid or missing API key from {request.client.host}")
        return JSONResponse(
            status_code=401,
            content={"error": "Invalid or missing API key. Please provide X-API-Key header."}
        )
    
    return await call_next(request)

@app.middleware("http")
async def security_middleware(request: Request, call_next):
    """Security headers and rate limiting middleware"""
    client_ip = request.client.host if request.client else "unknown"
    
    # Rate limit for API (skip for public endpoints)
    if request.url.path not in ["/", "/health"]:
        if not rate_limit_check(client_ip, 'api'):
            logger.warning(f"Rate limit exceeded for {client_ip}")
            return JSONResponse(
                status_code=429, 
                content={"error": "Rate limit exceeded. Try again later."}
            )
    
    response = await call_next(request)
    
    # Add security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Cache-Control"] = "no-store, max-age=0"
    
    return response

# ============================================================================
# PUBLIC ENDPOINTS
# ============================================================================

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "healthy", 
        "service": "PamojaData Quality Engine", 
        "version": "1.0.0", 
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health")
async def health():
    """Detailed health check"""
    return {
        "status": "alive", 
        "timestamp": datetime.now().isoformat(),
        "active_jobs": len([j for j in jobs.values() if j.get("status") == "processing"])
    }

# ============================================================================
# PROTECTED ENDPOINTS (Require API Key)
# ============================================================================

@app.post("/api/quality/check")
async def check_quality(
    background_tasks: BackgroundTasks, 
    file: UploadFile = File(...), 
    request: Request = None
):
    """Upload and check data quality"""
    client_ip = request.client.host if request and request.client else "unknown"
    
    # Rate limit for uploads
    if not rate_limit_check(client_ip, 'upload'):
        logger.warning(f"Upload rate limit exceeded for {client_ip}")
        raise HTTPException(status_code=429, detail="Upload limit exceeded. Try again later.")
    
    # Validate file
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
    
    # Sanitize filename
    safe_filename = sanitize_filename(file.filename)
    
    # Check file extension
    allowed_extensions = {'.csv', '.xlsx', '.xls'}
    file_ext = Path(safe_filename).suffix.lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400, 
            detail=f"File type not allowed. Allowed: {', '.join(allowed_extensions)}"
        )
    
    # Read and validate size
    content = await file.read()
    if not validate_file_size(content):
        raise HTTPException(status_code=413, detail="File too large. Max 50MB.")
    
    job_id = str(uuid.uuid4())
    temp_dir = Path("data/quality_engine_temp")
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_path = temp_dir / f"{job_id}_{safe_filename}"
    
    # Secure write
    with open(temp_path, "wb") as buffer:
        buffer.write(content)
    
    jobs[job_id] = {
        "status": "processing", 
        "file_path": str(temp_path), 
        "started_at": datetime.now().isoformat(), 
        "client_ip": client_ip
    }
    
    logger.info(f"Quality check started: job_id={job_id}, client={client_ip}, file={safe_filename}")
    
    def process_quality():
        try:
            # Read CSV with row limit for safety
            df = pd.read_csv(temp_path, nrows=10000)
            
            # Sanitize column names
            df.columns = [re.sub(r'[^a-zA-Z0-9_]', '_', str(col)) for col in df.columns]
            
            # Calculate quality metrics
            total_cells = df.shape[0] * df.shape[1]
            missing_cells = df.isna().sum().sum()
            missing_pct = (missing_cells / total_cells * 100) if total_cells > 0 else 0
            
            duplicates = df.duplicated().sum()
            duplicate_rate = (duplicates / len(df) * 100) if len(df) > 0 else 0
            
            # Calculate quality score (0-1)
            completeness_score = 1 - (missing_pct / 100)
            uniqueness_score = 1 - (duplicate_rate / 100)
            quality_score = max(0, min(1, (completeness_score + uniqueness_score) / 2))
            
            # Determine grade
            if quality_score >= 0.9:
                grade = 'A'
            elif quality_score >= 0.8:
                grade = 'B'
            elif quality_score >= 0.7:
                grade = 'C'
            elif quality_score >= 0.6:
                grade = 'D'
            else:
                grade = 'F'
            
            results = {
                'quality_score': round(quality_score, 3), 
                'quality_grade': grade, 
                'passed_checks': 3 if quality_score > 0.7 else 1, 
                'failed_checks': 0 if quality_score > 0.7 else 2, 
                'critical_issues': [] if quality_score > 0.7 else ['Data quality needs improvement'], 
                'recommendations': ['Data looks good'] if quality_score > 0.7 else ['Check for missing values and duplicates']
            }
            
            jobs[job_id].update({
                "status": "completed", 
                "results": results, 
                "completed_at": datetime.now().isoformat()
            })
            
            logger.info(f"Quality check completed: job_id={job_id}, score={quality_score}, grade={grade}")
            
            # Clean up temp file
            if os.path.exists(temp_path):
                os.remove(temp_path)
                
        except Exception as e:
            logger.error(f"Quality check failed: job_id={job_id}, error={str(e)}")
            jobs[job_id].update({
                "status": "failed", 
                "error": str(e), 
                "completed_at": datetime.now().isoformat()
            })
    
    background_tasks.add_task(process_quality)
    return JSONResponse({"job_id": job_id, "status": "processing"})

@app.get("/api/quality/result/{job_id}")
async def get_quality_result(job_id: str):
    """Get quality check results"""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = jobs[job_id]
    
    if job["status"] == "processing":
        return JSONResponse({"status": "processing", "job_id": job_id})
    
    if job["status"] == "failed":
        return JSONResponse({
            "status": "failed", 
            "error": job.get("error", "Unknown error")
        })
    
    return JSONResponse({
        "status": "completed",
        "job_id": job_id,
        "quality_score": job["results"]["quality_score"],
        "quality_grade": job["results"]["quality_grade"],
        "passed_checks": job["results"]["passed_checks"],
        "failed_checks": job["results"]["failed_checks"],
        "critical_issues": job["results"]["critical_issues"],
        "recommendations": job["results"]["recommendations"]
    })

@app.post("/api/data/clean")
async def clean_data(
    background_tasks: BackgroundTasks, 
    file: UploadFile = File(...), 
    request: Request = None
):
    """Upload and clean data"""
    client_ip = request.client.host if request and request.client else "unknown"
    
    if not rate_limit_check(client_ip, 'upload'):
        logger.warning(f"Clean upload rate limit exceeded for {client_ip}")
        raise HTTPException(status_code=429, detail="Upload limit exceeded.")
    
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
    
    safe_filename = sanitize_filename(file.filename)
    content = await file.read()
    
    if not validate_file_size(content):
        raise HTTPException(status_code=413, detail="File too large. Max 50MB.")
    
    job_id = str(uuid.uuid4())
    temp_dir = Path("data/quality_engine_temp")
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_path = temp_dir / f"{job_id}_{safe_filename}"
    
    with open(temp_path, "wb") as buffer:
        buffer.write(content)
    
    output_dir = Path("data/quality_engine_cleaned")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{job_id}_cleaned.csv"
    
    jobs[job_id] = {
        "status": "processing", 
        "output_path": str(output_path), 
        "started_at": datetime.now().isoformat()
    }
    
    logger.info(f"Data cleaning started: job_id={job_id}, client={client_ip}, file={safe_filename}")
    
    def process_cleaning():
        try:
            df = pd.read_csv(temp_path)
            original_rows = len(df)
            
            # Remove duplicates
            df = df.drop_duplicates()
            
            # Fill missing values
            for col in df.select_dtypes(include=['number']).columns:
                df[col] = df[col].fillna(df[col].median())
            
            for col in df.select_dtypes(include=['object']).columns:
                df[col] = df[col].fillna('Unknown')
                df[col] = df[col].astype(str).str.strip()
            
            df.to_csv(output_path, index=False)
            
            # Clean up temp file
            if os.path.exists(temp_path):
                os.remove(temp_path)
            
            cleaned_rows = len(df)
            logger.info(f"Data cleaning completed: job_id={job_id}, rows={original_rows}->{cleaned_rows}")
            
            jobs[job_id].update({
                "status": "completed", 
                "completed_at": datetime.now().isoformat(),
                "original_rows": original_rows,
                "cleaned_rows": cleaned_rows
            })
        except Exception as e:
            logger.error(f"Data cleaning failed: job_id={job_id}, error={str(e)}")
            jobs[job_id].update({"status": "failed", "error": str(e)})
    
    background_tasks.add_task(process_cleaning)
    return JSONResponse({
        "job_id": job_id, 
        "status": "processing", 
        "download_url": f"/api/data/download/{job_id}"
    })

@app.get("/api/data/download/{job_id}")
async def download_cleaned_data(job_id: str):
    """Download cleaned data file"""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = jobs[job_id]
    
    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail="Cleaning not completed")
    
    if not os.path.exists(job["output_path"]):
        raise HTTPException(status_code=404, detail="File not found")
    
    logger.info(f"Downloading cleaned data: job_id={job_id}")
    
    return FileResponse(
        path=job["output_path"],
        filename=f"cleaned_{job_id}.csv",
        media_type="text/csv"
    )

@app.get("/api/stats")
async def get_stats():
    """Get system statistics"""
    return {
        "total_jobs": len(jobs),
        "completed_jobs": sum(1 for j in jobs.values() if j.get("status") == "completed"),
        "failed_jobs": sum(1 for j in jobs.values() if j.get("status") == "failed"),
        "processing_jobs": sum(1 for j in jobs.values() if j.get("status") == "processing"),
        "api_key_configured": bool(API_KEY)
    }

# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    print("=" * 50)
    print("PamojaData Quality Engine API")
    print("=" * 50)
    print(f"Starting server on http://0.0.0.0:8001")
    print(f"API Docs: http://localhost:8001/docs")
    print("=" * 50)
    print(f"🔑 YOUR API KEY: {API_KEY}")
    print("=" * 50)
    print("")
    print("⚠️  IMPORTANT SECURITY NOTES:")
    print("   - Copy the API key above - you'll need it!")
    print("   - Include header: X-API-Key: YOUR_API_KEY")
    print("   - Rate limiting: 100 requests/minute, 10 uploads/5 minutes")
    print("   - Max file size: 50MB")
    print("   - Allowed file types: .csv, .xlsx, .xls")
    print("=" * 50)
    
    uvicorn.run(app, host="0.0.0.0", port=8001)