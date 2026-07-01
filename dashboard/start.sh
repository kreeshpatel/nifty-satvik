#!/bin/bash
echo "Starting NiftyQuant Dashboard..."
echo ""
echo "Backend: http://localhost:8000"
echo "Frontend: http://localhost:5173"
echo "API docs: http://localhost:8000/docs"
echo ""

cd "$(dirname "$0")/backend" && uvicorn main:app --reload --port 8000 &
cd "$(dirname "$0")/frontend" && npm run dev &

wait
