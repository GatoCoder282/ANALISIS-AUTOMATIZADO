# Render deployment Dockerfile for Streamlit + Selenium
FROM python:3.11-slim

# Install Chrome stable instead of Chromium for better compatibility
RUN apt-get update && apt-get install -y \
    wget \
    unzip \
    gnupg \
    && wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

ENV CHROME_BIN=/usr/bin/google-chrome \
    CHROME_HEADLESS=true \
    STREAMLIT_SERVER_PORT=10000

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# Expose Render's default web service port (can be overridden)
EXPOSE 10000

CMD ["streamlit", "run", "dashboards/app.py", "--server.port=10000", "--server.address=0.0.0.0", "--server.headless=true"]
