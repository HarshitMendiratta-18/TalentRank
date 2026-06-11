# Use an official lightweight Python image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY rank.py .
COPY sample_candidates.json .
COPY AI-Recruiter/ ./AI-Recruiter/

# Pre-download SentenceTransformer weights so they are built into the image
RUN python AI-Recruiter/download_model.py

# Expose the default port for Hugging Face Spaces / cloud platforms
EXPOSE 7860

# Run FastAPI app using Uvicorn on port 7860
CMD ["uvicorn", "AI-Recruiter.api.server:app", "--host", "0.0.0.0", "--port", "7860"]
