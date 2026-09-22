FROM python:3.12-slim

WORKDIR /opt/tydex

COPY pyproject.toml README.md LICENSE ./
COPY tydex ./tydex

RUN pip install --no-cache-dir .

EXPOSE 8000

CMD ["python", "-m", "tydex.server", "--host", "0.0.0.0", "--port", "8000"]