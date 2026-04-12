"""Dump the FastAPI OpenAPI schema to stdout as JSON."""

import json
import sys

from app.main import app

json.dump(app.openapi(), sys.stdout, indent=2)
sys.stdout.write("\n")
