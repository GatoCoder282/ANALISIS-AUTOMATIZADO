# Render deployment Dockerfile for Streamlit + Selenium
FROM python:3.11-slim

# Install Chrome stable instead of Chromium for better compatibility
RUN apt-get update && apt-get install -y \
    wget \
    unzip \
    gnupg \
    ca-certificates \
    && wget -q -O /tmp/google-chrome.gpg https://dl-ssl.google.com/linux/linux_signing_key.pub \
    && gpg --dearmor -o /usr/share/keyrings/google-chrome-keyring.gpg /tmp/google-chrome.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome-keyring.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/* /tmp/google-chrome.gpg

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
