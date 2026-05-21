# Dockerfile for PamojaData Humanitarian Platform with Quality Engine
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0
ENV QUALITY_ENGINE_PORT=8000

# Install system dependencies (including curl for health checks)
RUN apt-get update && apt-get install -y \
    gcc \
    sqlite3 \
    libsqlite3-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (better caching)
COPY requirements.txt .
COPY requirements-engine.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir -r requirements-engine.txt

# Copy the rest of the application
COPY . .

# Create necessary directories
RUN mkdir -p secure_data backups logs .streamlit
RUN mkdir -p quality_engine_data quality_engine_logs quality_engine_temp

# Create startup script
RUN echo '#!/bin/bash\n\
echo "========================================="\n\
echo "Starting PamojaData with Quality Engine"\n\
echo "========================================="\n\
\n\
# Start Quality Engine API in background\n\
echo "Starting Quality Engine API on port 8000..."\n\
python -c "\n\
import uvicorn\n\
import sys\n\
import os\n\
from pathlib import Path\n\
\n\
# Add to path\n\
sys.path.insert(0, \"/app\")\n\
\n\
# Import and run API\n\
try:\n\
    from quality_engine_api.server import app\n\
    uvicorn.run(app, host=\"0.0.0.0\", port=8000, log_level=\"warning\")\n\
except Exception as e:\n\
    print(f\"Error starting Quality Engine: {e}\")\n\
    # Keep running without engine\n\
    import time\n\
    while True:\n\
        time.sleep(60)\n\
" &\n\
\n\
# Wait for API to be ready\n\
echo "Waiting for Quality Engine API..."\n\
sleep 5\n\
\n\
# Test API connection\n\
if curl -s http://localhost:8000/ > /dev/null; then\n\
    echo "✅ Quality Engine API is running"\n\
else\n\
    echo "⚠️ Quality Engine API may not be ready yet"\n\
fi\n\
\n\
# Start Streamlit app (foreground)\n\
echo "Starting PamojaData on port 8501..."\n\
exec streamlit run app.py --server.port=8501 --server.address=0.0.0.0\n\
' > /app/start.sh && chmod +x /app/start.sh

# Expose ports
EXPOSE 8501
EXPOSE 8000

# Health check for the main app
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# Run the startup script
CMD ["/app/start.sh"]