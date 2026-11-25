from .errors import integer
from .selection import source_clock


def envelope(audio, first, last, bins):
    result = [[] for _ in range(audio.channels)]
    width = last - first
    bins = min(width, bins)
    for bucket in range(bins):
        low = first + bucket * width // bins
        high = first + (bucket + 1) * width // bins
        for channel in range(audio.channels):
            values = audio.pcm[low * audio.channels + channel:high * audio.channels:audio.channels]
            result[channel].append((min(values), max(values)))
    return result


def waveform(capture, selection, bins):
    bins = integer(bins, '波形桶数', 16, 512)
    clock = source_clock(capture, selection.offset)
    first, last = clock.sample(selection.start), clock.sample(selection.end)
    return dict(first_sample=first, end_sample=last, peaks=envelope(capture.audio, first, last, bins))
