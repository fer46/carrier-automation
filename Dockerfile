FROM python:3.13-slim

WORKDIR /app

# Install Node.js for building the dashboard
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy everything
COPY . .

# Build the React dashboard
# VITE_API_KEY is passed as a build arg so it gets baked into the static JS
ARG VITE_API_KEY=""
RUN cd dashboard && npm install && VITE_API_KEY=${VITE_API_KEY} npm run build

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
