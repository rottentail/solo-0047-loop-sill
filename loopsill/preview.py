from dataclasses import dataclass

from .identity import identity
from .metrics import boundary, measure
from .pcm import Audio
from .picture import render_picture
from .plan import LoopPlan, make_plan
from .sound import render_sound


@dataclass(frozen=True)
class Preview:
    key: str
    plan: LoopPlan
    picture: tuple[bytes, ...]
    audio: Audio
    before: dict
    after: dict

    def record(self, video):
        return dict(id=self.key, plan=self.plan.record(), before=self.before, after=self.after,
                    width=video.width, height=video.height, sample_rate=self.audio.sample_rate,
                    fps=[video.rate.numerator, video.rate.denominator])


def compile_preview(capture, selection):
    plan = make_plan(capture, selection)
    picture = tuple(render_picture(capture.video, plan))
    audio = render_sound(capture.audio, plan)
    return Preview(identity([capture.id, selection.record()]), plan, picture, audio,
                   measure(capture, selection),
                   boundary(capture.video, audio, picture[0], picture[-1], 0, audio.frames))
