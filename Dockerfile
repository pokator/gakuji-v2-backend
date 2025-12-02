FROM python:3.11-slim

WORKDIR /app

# Install system deps for some packages (if needed)
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential git curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# If jamdict_data/jamdict.db exists in the image, also place a copy in
# Jamdict's default location (~/.jamdict/data) so `Jamdict()` can find it.
# Use `cp -n` to avoid overwriting and fail-safe with `|| true`.
RUN if [ -f ./jamdict_data/jamdict.db ]; then \
            mkdir -p /root/.jamdict/data && cp -n ./jamdict_data/jamdict.db /root/.jamdict/data/ || true; \
        fi

# default port (can be overridden by environment)
ENV PORT=8000

EXPOSE 8000

# Use shell form so $PORT is expanded at runtime
CMD ["sh", "-c", "gunicorn -k uvicorn.workers.UvicornWorker app.main:app --bind 0.0.0.0:$PORT --workers 1 --timeout 180 --graceful-timeout 180"]
