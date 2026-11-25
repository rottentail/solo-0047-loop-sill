from dataclasses import dataclass

from .clock import Clock, duration
from .selection import source_clock


@dataclass(frozen=True)
class Shot:
    tail: int
    head: int | None = None
    blend_index: int = 0


@dataclass(frozen=True)
class LoopPlan:
    shots: tuple[Shot, ...]
    source: Clock
    output: Clock
    overlap: int

    def record(self):
        bounds = self.output.boundaries(len(self.shots))
        return dict(frame_count=len(self.shots), sample_count=bounds[-1], boundaries=bounds,
                    frame_seconds=duration(self.output.rate, len(self.shots)),
                    overlap_at=len(self.shots) - self.overlap if self.overlap else None,
                    frames=[dict(tail=shot.tail, head=shot.head) for shot in self.shots])


def make_plan(capture, selection):
    start, end, width = selection.start, selection.end, selection.overlap
    direct = tuple(Shot(i) for i in range(start + width, end - width))
    blend = tuple(Shot(end - width + i, start + i, i) for i in range(width))
    return LoopPlan(direct + blend, source_clock(capture, selection.offset),
                    Clock(capture.video.rate, capture.audio.sample_rate), width)
