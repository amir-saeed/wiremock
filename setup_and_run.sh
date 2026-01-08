#!/bin/bash
set -e

echo "=== WireMock Lambda Mock Setup ==="

# Check if poetry is installed
if ! command -v poetry &> /dev/null; then
    echo "Installing Poetry..."
    curl -sSL https://install.python-poetry.org | python3 -
fi

# Install dependencies
echo "Installing dependencies..."
poetry install

# Start WireMock (use docker compose V2)
echo "Starting WireMock..."
if command -v docker-compose &> /dev/null; then
    docker-compose up -d
elif command -v docker &> /dev/null && docker compose version &> /dev/null; then
    docker compose up -d
else
    echo "Error: Neither 'docker-compose' nor 'docker compose' found"
    exit 1
fi

# Wait for WireMock
echo "Waiting for WireMock to start..."
sleep 5

# Run demo
echo "Running demo..."
poetry run python run_demo.py

echo ""
echo "=== Setup Complete ==="
echo "WireMock Admin UI: http://localhost:8080/__admin/"
echo ""
echo "To run tests: poetry run pytest tests/ -v"
echo "To stop WireMock: docker compose down"