FROM python:3.11-slim
WORKDIR /app

# Copy and install dependencies first for better caching
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy only the source files needed for the application
COPY *.py .
COPY bots/ ./bots/

EXPOSE 8100
CMD ["python", "start_servers.py"]