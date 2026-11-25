from array import array

from .clock import nearest
from .pcm import Audio


def sample_from_span(audio, span, position, length, channel):
    """区间内的中心对齐线性采样，端点夹持。"""
    first, last = span
    width = last - first
    if width == length:
        return audio.sample(first + position, channel)
    scale = 2 * length
    location = (2 * position + 1) * width - length
    left, fraction = divmod(location, scale)
    if left < 0:
        return audio.sample(first, channel)
    if left >= width - 1:
        return audio.sample(last - 1, channel)
    a = audio.sample(first + left, channel)
    b = audio.sample(first + left + 1, channel)
    return nearest(a * (scale - fraction) + b * fraction, scale)


def render_sound(audio, plan):
    samples = array('h')
    overlap_at = len(plan.shots) - plan.overlap
    blend_start = plan.output.sample(overlap_at)
    blend_length = plan.output.sample(len(plan.shots)) - blend_start
    for frame, shot in enumerate(plan.shots):
        first, last = plan.output.span(frame)
        tail = plan.source.span(shot.tail)
        head = plan.source.span(shot.head) if shot.head is not None else None
        if head is None and tail[1] - tail[0] == last - first:
            samples.extend(audio.pcm[tail[0] * audio.channels:tail[1] * audio.channels])
            continue
        for position in range(last - first):
            for channel in range(audio.channels):
                left = sample_from_span(audio, tail, position, last - first, channel)
                if head is not None:
                    right = sample_from_span(audio, head, position, last - first, channel)
                    weight = first - blend_start + position + 1
                    if blend_length > 1:
                        weight -= 1
                    scale = max(1, blend_length - 1)
                    left = nearest(left * (scale - weight) + right * weight, scale)
                samples.append(left)
    return Audio(audio.sample_rate, audio.channels, samples)
