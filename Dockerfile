# Use official Python image
FROM python:3.11-slim

# Install Rust and system packages
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    gcc \
    libffi-dev \
    libssl-dev \
    pkg-config \
    git \
 && curl https://sh.rustup.rs -sSf | sh -s -- -y \
 && . "$HOME/.cargo/env"

# Set environment so cargo is available
ENV PATH="/root/.cargo/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy all project files
COPY . .

# Install Python dependencies
RUN pip install --upgrade pip && pip install -r requirements.txt

# Expose port for FastAPI
EXPOSE 8000

# Run FastAPI with uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
