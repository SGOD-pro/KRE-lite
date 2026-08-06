FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the app package to /app
# So /app/app will be the actual python package. Wait, if the WORKDIR is /app, and we copy ./app to /app/app, it works if uvicorn runs app.api.main:app.
# Let's just copy the root directory contents, but we only need /app.
COPY ./app ./app

CMD ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
