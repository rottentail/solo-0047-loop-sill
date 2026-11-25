from contextlib import closing, contextmanager
from pathlib import Path
import json
import sqlite3

from .errors import MediaError
from .identity import json_bytes

SCHEMA = '''
CREATE TABLE IF NOT EXISTS capture (
    id TEXT PRIMARY KEY, label TEXT NOT NULL, picture BLOB NOT NULL,
    sound BLOB NOT NULL, facts TEXT NOT NULL, suggested TEXT
);
CREATE TABLE IF NOT EXISTS draft (
    capture_id TEXT NOT NULL REFERENCES capture(id), revision INTEGER NOT NULL,
    choice TEXT NOT NULL, PRIMARY KEY(capture_id, revision)
);
CREATE TABLE IF NOT EXISTS handoff (
    id TEXT PRIMARY KEY, capture_id TEXT NOT NULL, revision INTEGER NOT NULL,
    summary TEXT NOT NULL, bundle BLOB NOT NULL,
    FOREIGN KEY(capture_id, revision) REFERENCES draft(capture_id, revision),
    UNIQUE(capture_id, revision)
);
'''


def decode(value):
    return json.loads(value) if value is not None else None


class Store:
    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.database = self.root / 'projection.sqlite3'
        with self.connect() as db:
            db.execute('PRAGMA journal_mode = WAL')
            db.executescript(SCHEMA)

    @contextmanager
    def connect(self):
        with closing(sqlite3.connect(self.database, timeout=10)) as db:
            db.row_factory = sqlite3.Row
            db.execute('PRAGMA foreign_keys = ON')
            with db:
                yield db

    def register(self, capture, picture, sound, label, suggested):
        with self.connect() as db:
            db.execute('INSERT OR IGNORE INTO capture VALUES (?, ?, ?, ?, ?, ?)',
                       (capture.id, label, picture, sound, json_bytes(capture.facts()), json_bytes(suggested)))
        return self.capture_info(capture.id)

    @staticmethod
    def capture_record(row):
        return dict(**decode(row['facts']), label=row['label'], suggested=decode(row['suggested']))

    def captures(self):
        with self.connect() as db:
            return [self.capture_record(row) for row in db.execute('SELECT label, facts, suggested FROM capture ORDER BY rowid DESC')]

    def capture_info(self, key):
        with self.connect() as db:
            row = db.execute('SELECT label, facts, suggested FROM capture WHERE id = ?', (key,)).fetchone()
        if row is None:
            raise MediaError('配对素材不存在', status=404)
        return self.capture_record(row)

    def source_bytes(self, key):
        with self.connect() as db:
            row = db.execute('SELECT picture, sound FROM capture WHERE id = ?', (key,)).fetchone()
        if row is None:
            raise MediaError('配对素材不存在', status=404)
        return row['picture'], row['sound']

    def save(self, key, selection, expected):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            latest = db.execute('SELECT coalesce(max(revision), 0) FROM draft WHERE capture_id = ?', (key,)).fetchone()[0]
            if latest != expected:
                raise MediaError(f'接缝稿已更新，目前为第 {latest} 稿', status=409)
            revision = latest + 1
            db.execute('INSERT INTO draft VALUES (?, ?, ?)', (key, revision, json_bytes(selection.record())))
        return dict(revision=revision, selection=selection.record())

    def drafts(self, key):
        self.capture_info(key)
        with self.connect() as db:
            rows = db.execute('SELECT revision, choice FROM draft WHERE capture_id = ? ORDER BY revision DESC', (key,))
            return [dict(revision=row['revision'], selection=decode(row['choice'])) for row in rows]

    def draft(self, key, rev):
        with self.connect() as db:
            row = db.execute('SELECT choice FROM draft WHERE capture_id = ? AND revision = ?', (key, rev)).fetchone()
        if row is None:
            raise MediaError('接缝稿不存在', status=404)
        return decode(row[0])

    def put_handoff(self, summary, blob):
        with self.connect() as db:
            db.execute('INSERT OR IGNORE INTO handoff VALUES (?, ?, ?, ?, ?)',
                       (summary['id'], summary['capture_id'], summary['revision'], json_bytes(summary), blob))
        return self.handoff_by_revision(summary['capture_id'], summary['revision'])

    def handoff_by_revision(self, key, revision):
        with self.connect() as db:
            row = db.execute('SELECT summary FROM handoff WHERE capture_id = ? AND revision = ?', (key, revision)).fetchone()
            return decode(row[0]) if row is not None else None

    def handoffs(self, key):
        self.capture_info(key)
        with self.connect() as db:
            return [decode(row[0]) for row in db.execute('SELECT summary FROM handoff WHERE capture_id = ? ORDER BY revision DESC', (key,))]

    def handoff(self, key):
        with self.connect() as db:
            row = db.execute('SELECT summary, bundle FROM handoff WHERE id = ?', (key,)).fetchone()
        if row is None:
            raise MediaError('封存环带不存在', status=404)
        return decode(row[0]), row[1]
