#!/bin/sh
if [ "$ENVIRONMENT" = "production" ]; then
    exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
else
    exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
fi
