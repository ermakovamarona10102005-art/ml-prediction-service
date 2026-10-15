FROM python:3.9-slim

WORKDIR /app

COPY app/requirements.txt .
RUN pip install --no-cache-dir --default-timeout=1200 --retries=10 -r requirements.txt

COPY app/ .
COPY model/ /model/

EXPOSE 5000

CMD ["python", "app.py"]
