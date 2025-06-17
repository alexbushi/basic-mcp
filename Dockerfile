FROM python:3.12-slim

WORKDIR /app

RUN pip install uv

COPY requirements.txt .

RUN uv venv && uv pip install -r requirements.txt

COPY server.py .
COPY client.py .

EXPOSE 8050

CMD ["uv", "run", "server.py"] 