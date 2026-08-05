import os
import sys
import importlib
from pathlib import Path
import tempfile
from types import SimpleNamespace

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_DIR = PROJECT_ROOT / "app"
for import_path in (PROJECT_ROOT, APP_DIR):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

os.environ.setdefault("PYTEST_CURRENT_TEST", "collection")
app_db = importlib.import_module("app.db")
sys.modules["db"] = app_db


@pytest.fixture()
def temp_db(monkeypatch):
    # Create temp sqlite file and init schema
    fd, path = tempfile.mkstemp(prefix="test_meas_", suffix=".db")
    os.close(fd)
    monkeypatch.setattr(app_db, "db_name", path, raising=True)
    # Initialize schema via Alembic migrations
    app_db.run_migrations(path)
    try:
        yield path
    finally:
        try:
            os.remove(path)
        except FileNotFoundError:
            pass


class DummyMessage:
    def __init__(self):
        self.text = "callback message"
        self.texts = []
        self.kwargs = []
        self.photos = []
        self.photo_kwargs = []
        self.documents = []
        self.document_kwargs = []
        self.chat = SimpleNamespace(id=123)

    async def reply_text(self, text, **kwargs):
        self.texts.append(text)
        self.kwargs.append(kwargs)

    async def reply_photo(self, photo, **kwargs):
        self.photos.append(photo.read())
        self.photo_kwargs.append(kwargs)

    async def reply_document(self, document, **kwargs):
        self.documents.append(document.read())
        self.document_kwargs.append(kwargs)


class DummyCallbackQuery:
    def __init__(self):
        self.message = DummyMessage()
        self.edited_texts = []
        self.edit_kwargs = []
        self.data = None

    async def answer(self):
        # No-op for tests
        return

    async def edit_message_text(self, text, **kwargs):
        self.edited_texts.append(text)
        self.edit_kwargs.append(kwargs)


class DummyUser:
    def __init__(self, user_id=1, first_name="Test", last_name="User", username="tester"):
        self.id = user_id
        self.first_name = first_name
        self.last_name = last_name
        self.username = username


@pytest.fixture()
def dummy_update():
    update = SimpleNamespace()
    update.effective_user = DummyUser(user_id=999)
    update.message = DummyMessage()
    update.callback_query = DummyCallbackQuery()
    update.effective_message = update.callback_query.message
    update.effective_chat = SimpleNamespace(id=123)
    return update


@pytest.fixture()
def dummy_context():
    ctx = SimpleNamespace()
    ctx.user_data = {}
    return ctx
