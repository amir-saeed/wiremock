# wiremock
Mock AWS Lambda invoke endpoints using WireMock with JSON stub responses and templating.

Requirements:
- Python 3.12
- Docker + Docker Compose
- Poetry

Setup:
- docker compose up -d
- poetry env use python3.12
- poetry install

Run tests:
- poetry run pytest
