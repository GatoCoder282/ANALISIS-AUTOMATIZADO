# Render deployment Dockerfile for Streamlit + Selenium
FROM python:3.11-slim

# Install Chromium and chromedriver
RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    fonts-liberation \
    wget \
    && rm -rf /var/lib/apt/lists/*

ENV CHROME_BIN=/usr/bin/chromium \
    CHROMEDRIVER_PATH=/usr/bin/chromedriver \
    CHROME_HEADLESS=true \
    STREAMLIT_SERVER_PORT=10000

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# Expose Render's default web service port (can be overridden)
EXPOSE 10000

CMD ["streamlit", "run", "dashboards/app.py", "--server.port=10000", "--server.headless=true", "--server.enableCORS=true"]
