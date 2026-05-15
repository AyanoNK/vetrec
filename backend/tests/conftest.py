import os

# Set safe defaults before any test module imports app.main. Individual tests
# can still override via monkeypatch.setenv / monkeypatch.delenv as needed.
os.environ.setdefault("FIREWORKS_API_KEY", "fk-test")
os.environ.setdefault("LLM_MODEL", "accounts/fireworks/models/glm-5p1")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:5173")
