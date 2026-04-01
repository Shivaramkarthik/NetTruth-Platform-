#!/bin/bash
echo "Starting NetTruth on port $PORT"
uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8000}