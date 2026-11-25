from array import array

from .clock import Clock
from .errors import MediaError, integer
from .limits import MAX_OUTPUT_BYTES
from .pcm import Audio
from .sound import sample_from_span


def repeat_samples(video, audio, turns):
    turns = integer(turns, '排练圈数', 1, 96)
    frames = len(video.frames)
    clock = Clock(video.rate, audio.sample_rate)
    boundaries = [clock.sample(frames * i) for i in range(turns + 1)]
    estimate = turns * frames * (len(video.frames[0]) + 6) + boundaries[-1] * audio.channels * 2 + 4096
    if estimate > MAX_OUTPUT_BYTES:
        raise MediaError('排练输出超过大小上限', status=413)
    samples = array('h')
    for first, last in zip(boundaries, boundaries[1:]):
        width = last - first
        if width == audio.frames:
            samples.extend(audio.pcm)
        else:
            for index in range(width):
                for channel in range(audio.channels):
                    samples.append(sample_from_span(audio, (0, audio.frames), index, width, channel))
    return Audio(audio.sample_rate, audio.channels, samples), boundaries
