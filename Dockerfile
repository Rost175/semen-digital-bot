FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt /app/requirements.txt

RUN pip uninstall -y telegram && \
    pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir python-telegram-bot==22.7 && \
    pip install --no-cache-dir -r requirements.txt

COPY . /app

CMD ["python", "semen_digital_bot.py"]
