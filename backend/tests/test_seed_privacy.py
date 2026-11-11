"""Privacy regression tests for demonstration-data seeding."""
from types import SimpleNamespace
from unittest.mock import Mock

import app.seed as seed


class _Rows:
    def __init__(self, *, first=None, values=()):
        self._first = first
        self._values = values

    def first(self):
        return self._first

    def __iter__(self):
        return iter(self._values)


class _FakeDB:
    def __init__(self):
        self.added = []
        self.added_many = []

    def scalars(self, statement):
        # The first query loads competencies; the second checks for an existing demo document.
        if not hasattr(self, "_query_count"):
            self._query_count = 0
        self._query_count += 1
        if self._query_count == 1:
            return _Rows(values=[])
        return _Rows(first=None)

    def add(self, item):
        self.added.append(item)

    def add_all(self, items):
        self.added_many.extend(items)

    def flush(self):
        pass

    def commit(self):
        pass


def test_demo_seeding_does_not_send_document_text_without_explicit_opt_in(monkeypatch):
    text = (
        "Statistical sampling uses a probability design to select units from a target population. "
        "Stratification divides a heterogeneous population into internally homogeneous groups. "
        "Calibration adjusts design weights so known population totals are reproduced. "
    ) * 3
    monkeypatch.setattr(
        seed.fd,
        "DEMO_DOCUMENTS",
        [{
            "title": "Privacy Test Material",
            "filename": "privacy-test.txt",
            "content": text,
            "topic": "sampling",
            "competencies": [],
        }],
    )
    monkeypatch.setattr(seed, "store_file", lambda data, filename: ("privacy-test.txt", "a" * 64))
    monkeypatch.setattr(seed.settings, "ai_send_documents_externally", False)

    embed = Mock(side_effect=AssertionError("external embedding must not be called"))
    monkeypatch.setattr(seed, "ai", SimpleNamespace(enabled=True, embed=embed))

    db = _FakeDB()
    docs = seed.seed_demo_documents(db, admin=SimpleNamespace(id=None))

    assert len(docs) == 1
    assert docs[0].embedding_model is None
    assert db.added_many
    embed.assert_not_called()
