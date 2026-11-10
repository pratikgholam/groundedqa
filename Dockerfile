FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir --upgrade pip

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY db ./db

# Run as a non-root user to limit the blast radius of any container escape.
RUN useradd --create-home --shell /bin/bash groundedqa && \
    chown -R groundedqa:groundedqa /app
USER groundedqa

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
