import os
import sys
from pathlib import Path
import tempfile
from types import SimpleNamespace

import pytest


@pytest.fixture()
def temp_db(monkeypatch):
    # Create temp sqlite file and init schema
    # Ensure project root is on sys.path for `import app`
    project_root = Path(__file__).resolve().parents[1]
    app_dir = project_root / "app"
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    if str(app_dir) not in sys.path:
        sys.path.insert(0, str(app_dir))

    from app import db as app_db
    # Ensure 'db' module name points to the same module as 'app.db'
    sys.modules['db'] = app_db
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
        self.texts = []
        self.kwargs = []
        self.chat = SimpleNamespace(id=123)

    async def reply_text(self, text, **kwargs):
        self.texts.append(text)
        self.kwargs.append(kwargs)


class DummyCallbackQuery:
    def __init__(self):
        self.message = DummyMessage()
        self.edited_texts = []
        self.edit_kwargs = []

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
