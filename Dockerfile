FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && useradd -m -u 1000 nanga
COPY . .
RUN mkdir -p /app/data/private && chown -R nanga:nanga /app/data
USER nanga
EXPOSE 8787
CMD ["uvicorn","nanga.app:create_app","--factory","--host","0.0.0.0","--port","8787","--no-proxy-headers"]
