FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .

RUN useradd -m -u 1000 botuser && \
    chown -R botuser:botuser /app && \
    mkdir -p /tmp/bot_workspace && \
    chown botuser:botuser /tmp/bot_workspace

USER botuser
EXPOSE 8100
CMD ["python", "start_servers.py"]