#!/bin/bash

# Kill any existing port-forwards
pkill -f "kubectl port-forward"

# Start port-forwarding in the background
kubectl port-forward svc/vinci4d-backend 30001:8000 &
kubectl port-forward svc/vinci4d-postgres 30002:5432 &

echo "Port forwarding set up:"
echo "Backend: localhost:8000 -> vinci4d-backend:8000"
echo "PostgreSQL: localhost:5432 -> vinci4d-postgres:5432"
echo "Press Ctrl+C to stop"

# Wait for Ctrl+C
trap "pkill -f 'kubectl port-forward'; echo 'Port forwarding stopped'" INT
wait