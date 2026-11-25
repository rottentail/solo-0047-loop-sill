from dataclasses import dataclass

from .identity import digest, identity
from .pcm import Audio, parse_wav
from .y4m import Video, parse_y4m


@dataclass(frozen=True)
class Capture:
    id: str
    video_hash: str
    audio_hash: str
    video: Video
    audio: Audio

    def facts(self):
        return dict(id=self.id, video_sha256=self.video_hash, audio_sha256=self.audio_hash,
                    width=self.video.width, height=self.video.height, frame_count=len(self.video.frames),
                    fps=[self.video.rate.numerator, self.video.rate.denominator],
                    channels=self.audio.channels, sample_rate=self.audio.sample_rate,
                    sample_count=self.audio.frames)


def decode_capture(picture, sound):
    video = parse_y4m(picture)
    audio = parse_wav(sound)
    video_hash, audio_hash = digest(picture), digest(sound)
    return Capture(identity([video_hash, audio_hash]), video_hash, audio_hash, video, audio)
