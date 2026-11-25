from dataclasses import asdict, dataclass

from .clock import Clock
from .errors import MediaError, integer, object_fields
from .limits import MAX_OVERLAP, MAX_SECONDS


@dataclass(frozen=True)
class Selection:
    start: int
    end: int
    overlap: int
    offset: int

    def record(self):
        return asdict(self)


def interpret(capture, payload):
    object_fields(payload, ('start', 'end', 'overlap', 'offset'))
    max_frame = len(capture.video.frames)
    start = integer(payload['start'], '首格', 0, max_frame - 4)
    end = integer(payload['end'], '末端界线', start + 4, max_frame)
    overlap = integer(payload['overlap'], '交叠格数', 0, min(MAX_OVERLAP, (end - start - 2) // 2))
    limit = capture.audio.sample_rate * MAX_SECONDS
    offset = integer(payload['offset'], '拾音偏移', -limit, limit)
    clock = source_clock(capture, offset)
    first, last = clock.sample(start), clock.sample(end)
    if first < 0 or last > capture.audio.frames:
        raise MediaError(f'拾音覆盖不足：所需样本 [{first}, {last})，实际 [0, {capture.audio.frames})', status=422)
    return Selection(start, end, overlap, offset)


def source_clock(capture, offset):
    return Clock(capture.video.rate, capture.audio.sample_rate, offset)


def available(capture):
    clock = source_clock(capture, 0)
    end = max(i for i in range(len(capture.video.frames) + 1) if clock.sample(i) <= capture.audio.frames)
    if end < 4:
        return None
    return Selection(0, end, min(4, (end - 2) // 2), 0).record()
