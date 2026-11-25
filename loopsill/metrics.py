from math import sqrt

from .picture import luma_difference
from .selection import source_clock


def audio_edge(audio, pre, post, width):
    result = []
    for channel in range(audio.channels):
        deltas = (audio.sample(pre - width + i, channel) - audio.sample(post + i, channel) for i in range(width))
        result.append(dict(jump=abs(audio.sample(pre - 1, channel) - audio.sample(post, channel)) / 65535,
                           window_rms=sqrt(sum(d * d for d in deltas) / width) / 65535))
    return result


def boundary(video, audio, first_frame, last_frame, first_sample, last_sample):
    width = min(audio.sample_rate // 100, last_sample - first_sample)
    return dict(luma=luma_difference(last_frame, first_frame, video.width, video.height),
                channels=audio_edge(audio, last_sample, first_sample, width), window_samples=width)


def measure(capture, selection):
    first, last = selection.start, selection.end
    clock = source_clock(capture, selection.offset)
    start_sample, end_sample = clock.sample(first), clock.sample(last)
    facts = boundary(capture.video, capture.audio, capture.video.frames[first],
                     capture.video.frames[last - 1], start_sample, end_sample)
    facts.update(first_sample=start_sample, end_sample=end_sample)
    return facts
