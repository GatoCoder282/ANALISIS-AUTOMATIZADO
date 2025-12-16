# Render deployment Dockerfile for Streamlit + Selenium
FROM python:3.11-slim

# Install dependencies and Chromium
RUN apt-get update && apt-get install -y \
    chromium \
    fonts-liberation \
    libglib2.0-0 \
    libnss3 \
    libgconf-2-4 \
    libfontconfig1 \
    wget \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Download compatible ChromeDriver for Chromium 143
RUN CHROMEDRIVER_VERSION=131.0.6778.204 && \
    wget -q "https://storage.googleapis.com/chrome-for-testing-public/${CHROMEDRIVER_VERSION}/linux64/chromedriver-linux64.zip" -O /tmp/chromedriver.zip && \
    unzip /tmp/chromedriver.zip -d /tmp/ && \
    mv /tmp/chromedriver-linux64/chromedriver /usr/local/bin/chromedriver && \
    chmod +x /usr/local/bin/chromedriver && \
    rm -rf /tmp/chromedriver.zip /tmp/chromedriver-linux64

ENV CHROME_BIN=/usr/bin/chromium \
    CHROMEDRIVER_PATH=/usr/local/bin/chromedriver \
    CHROME_HEADLESS=true \
    STREAMLIT_SERVER_PORT=10000

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# Expose Render's default web service port (can be overridden)
EXPOSE 10000

CMD ["streamlit", "run", "dashboards/app.py", "--server.port=10000", "--server.address=0.0.0.0", "--server.headless=true"]
