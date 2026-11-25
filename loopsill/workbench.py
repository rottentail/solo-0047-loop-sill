from functools import lru_cache

from .demos import DEMO_LABELS, demo_capture
from .errors import MediaError, integer
from .identity import valid_id
from .handoff import make_handoff
from .metrics import measure
from .preview import compile_preview
from .raster import atlas_info, atlas_png, frame_png
from .search import scan
from .selection import available, interpret
from .source import decode_capture
from .store import Store
from .waveform import waveform


class Workbench:
    def __init__(self, root):
        self.store = Store(root)
        self._load = lru_cache(maxsize=2)(self._read_source)
        self._preview = lru_cache(maxsize=2)(self._render)
        self._sheet = lru_cache(maxsize=12)(self._render_sheet)

    def _read_source(self, key):
        source = decode_capture(*self.store.source_bytes(key))
        if source.id != key:
            raise MediaError('保存的素材与登记编号不符', status=500)
        return source

    def capture(self, key):
        return self._load(valid_id(key))

    def register(self, label, picture, sound, suggested=None):
        if not isinstance(label, str) or not label.strip() or len(label) > 80 or not label.isprintable():
            raise MediaError('素材名称须为 1 至 80 个可见字符')
        item = decode_capture(picture, sound)
        return self.store.register(item, picture, sound, label.strip(), suggested or available(item))

    def demo(self, kind):
        picture, sound, selection = demo_capture(kind)
        return self.register(DEMO_LABELS[kind], picture, sound, selection)

    def choice(self, key, raw):
        return interpret(self.capture(key), raw)

    def measure(self, key, raw):
        capture = self.capture(key)
        return measure(capture, interpret(capture, raw))

    def scan(self, key, raw, radius, focus):
        capture = self.capture(key)
        return scan(capture, interpret(capture, raw), radius, focus)

    def waveform(self, key, raw, bins):
        capture = self.capture(key)
        return waveform(capture, interpret(capture, raw), bins)

    def source_frame(self, key, index):
        video = self.capture(key).video
        return frame_png(video, video.frames[integer(index, '来源画格', 0, len(video.frames) - 1)])

    def _render(self, key, selection):
        return compile_preview(self.capture(key), selection)

    def preview(self, key, raw):
        return self._preview(key, self.choice(key, raw))

    def preview_info(self, key, raw):
        capture = self.capture(key)
        result = self.preview(key, raw)
        return dict(**result.record(capture.video), atlas=atlas_info(capture.video, len(result.picture)))

    def _render_sheet(self, key, selection, sheet):
        capture = self.capture(key)
        preview = self._preview(key, selection)
        return atlas_png(capture.video, preview.picture, sheet)

    def preview_sheet(self, key, raw, index):
        preview = self.preview(key, raw)
        count = atlas_info(self.capture(key).video, len(preview.picture))['sheets']
        return self._sheet(key, self.choice(key, raw), integer(index, '预演页', 0, count - 1))

    def save(self, key, raw, expected):
        expected = integer(expected, '预期稿号', 0, 2 ** 31 - 2)
        return self.store.save(key, self.choice(key, raw), expected)

    def freeze(self, key, revision):
        capture = self.capture(key)
        revision = integer(revision, '接缝稿编号', 1, 2 ** 31 - 1)
        raw = self.store.draft(key, revision)
        existing = self.store.handoff_by_revision(key, revision)
        if existing is not None:
            return existing
        selection = interpret(capture, raw)
        summary, blob = make_handoff(capture, selection, revision, self._preview(key, selection))
        return self.store.put_handoff(summary, blob)
