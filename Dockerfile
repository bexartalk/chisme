FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py admin.py autopush.py juanscores.py limits.py mascot.py namefilter.py ownerposts.py ownerposts_admin.py push.py qrsvg.py reader.py stats.py social.py social_api.py social_auth.py social_store.py website.py ./
COPY data ./data
COPY static ./static
COPY private ./private
ENV PORT=8080
EXPOSE 8080
CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port ${PORT}"]
