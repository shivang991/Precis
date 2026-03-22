import os

# Set required env vars before any app modules are imported so Settings validation passes.
os.environ.setdefault("GOOGLE_CLIENT_ID", "test-client-id")
os.environ.setdefault("GOOGLE_CLIENT_SECRET", "test-client-secret")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-tests-only")
