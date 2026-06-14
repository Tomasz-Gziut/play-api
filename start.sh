#!/bin/bash
set -e
echo "Building frontend..."
cd frontend
npm install
npm run build
cd ..
echo "Starting server on port ${PORT:-8000}"
uvicorn main:app --host 0.0.0.0 --port "${PORT:-8000}"
