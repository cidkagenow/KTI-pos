#!/bin/bash
# KTI-POS Startup Script
# Starts both backend (uvicorn) and frontend (vite dev)

PROJECT_DIR="/Users/cidkagenow/kti-pos"
LOG_DIR="$PROJECT_DIR/logs"
mkdir -p "$LOG_DIR"

# Start backend
cd "$PROJECT_DIR/backend"
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 \
  >> "$LOG_DIR/backend.log" 2>&1 &
BACKEND_PID=$!
echo "Backend started (PID: $BACKEND_PID)"

# Start frontend
cd "$PROJECT_DIR/frontend"
export PATH="/Users/cidkagenow/.nvm/versions/node/v23.1.0/bin:$PATH"
npm run dev -- --host 0.0.0.0 \
  >> "$LOG_DIR/frontend.log" 2>&1 &
FRONTEND_PID=$!
echo "Frontend started (PID: $FRONTEND_PID)"

echo "Backend PID: $BACKEND_PID" > "$LOG_DIR/pids.txt"
echo "Frontend PID: $FRONTEND_PID" >> "$LOG_DIR/pids.txt"
echo "KTI-POS is running. Logs in $LOG_DIR"
