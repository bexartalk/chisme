FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py admin.py autopush.py juanscores.py limits.py mascot.py namefilter.py push.py qrsvg.py reader.py stats.py website.py ./
COPY data ./data
COPY static ./static
ENV PORT=8080
EXPOSE 8080
CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port ${PORT}"]
