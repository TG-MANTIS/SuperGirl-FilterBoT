# --------------------------------------------------------------------------- #
#  Mantis Bots™ - Production Dockerfile                                       #
#  Optimized Python 3.10 Slim Image for Telegram Bot Deployment               #
# --------------------------------------------------------------------------- #

FROM python:3.10-slim

# Set environment variables to prevent interactive prompts and bytecode generation
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Update system packages and install essential utilities
RUN apt-get update && apt-get upgrade -y && \
    apt-get install -y --no-install-recommends git && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set working directory inside the container
WORKDIR /app

# Copy dependency requirements file first to leverage Docker layer caching
COPY requirements.txt .

# Upgrade pip and install Python dependencies securely without cache
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of the bot application code into the container
COPY . .

# Command to run the bot application
CMD ["python", "bot.py"]
