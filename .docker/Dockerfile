# Base image: Python 3.12 with uv
FROM ghcr.io/astral-sh/uv:python3.12-trixie

# Install system dependencies
RUN apt-get update 
RUN apt-get install -y \
    build-essential \
    libpq-dev \
    git

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# install dependencies
WORKDIR /tmp
COPY Pipfile Pipfile.lock .
RUN uvx pipenv requirements --dev > reqs.txt # pipenv install is longer
RUN uv pip install --system -r reqs.txt

# Expose Django port
EXPOSE 8000

# switch to app folder
WORKDIR /app
