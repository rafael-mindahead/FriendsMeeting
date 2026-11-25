import os
from tempfile import TemporaryDirectory

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://test:test@localhost:5432/test"
)


# Isolate media writes from the application and avoid /app permissions on CI.
_media_directory = TemporaryDirectory(prefix="friendsmeeting-tests-")
os.environ["UPLOAD_DIR"] = _media_directory.name
