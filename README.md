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


Best Practices for Shared Packages
Use a Private Registry (For Enterprise)
If you have many packages and multiple teams, using AWS CodeArtifact is the gold standard. It acts like a private version of PyPI. You can:

Publish your package to CodeArtifact.

Use pip install to pull it into your CI/CD pipeline.

Automate the Layer creation from there.

Managing External Dependencies
If your shared package depends on other libraries (like requests or pandas), you should install them into that same python/ folder before zipping:

Bash

pip install requests -t python/
Versioning
Every time you update a Layer, AWS creates a new Version (e.g., Version 1, Version 2). Lambda functions are locked to a specific version number, so updating a layer won't accidentally break your functions until you manually point them to the new version.
