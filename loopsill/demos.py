from array import array
from fractions import Fraction
from math import pi, sin

from .clock import Clock
from .errors import MediaError
from .pcm import Audio, encode_wav
from .y4m import Video, encode_y4m

DEMO_LABELS = {'pendulum': '青幕摆灯', 'counterbeat': '双节拍幕'}


def demo_frame(index, period, variant, width, height):
    phase = 2 * pi * index / period
    x_light = int(width * (.5 + .32 * sin(phase)))
    y_light = int(height * (.49 - .18 * sin(phase * 2)))
    points = bytearray()
    for y in range(height):
        for x in range(width):
            d2 = (x - x_light) ** 2 + (y - y_light) ** 2
            horizon = 9 if y % 9 == 0 else 0
            shutters = 15 if variant and (x + index * 2) % 38 < 3 else 0
            light = max(0, 161 - d2 // 5)
            points.append(27 + x * 30 // width + horizon + shutters + light)
    size = width * height // 4
    points.extend(bytes([142 + int(14 * sin(phase))]) * size)
    points.extend(bytes([103 + int(11 * sin(phase * 2))]) * size)
    return bytes(points)


def demo_capture(kind):
    if kind not in DEMO_LABELS:
        raise MediaError('演示素材不存在', status=404)
    alternate = kind == 'counterbeat'
    rate = Fraction(30000, 1001) if alternate else Fraction(24)
    sample_rate = 44100 if alternate else 24000
    width, height, frame_count = (128, 72, 82) if alternate else (128, 72, 76)
    period = 29 if alternate else 24
    frames = tuple(demo_frame(i, period, alternate, width, height) for i in range(frame_count))
    video = Video(width, height, rate, frames)
    clock = Clock(rate, sample_rate)
    pad = 937 if alternate else 0
    length = clock.sample(frame_count) + pad
    pcm = array('h')
    cycle = clock.sample(31 if alternate else period)
    for i in range(length):
        time = (i - pad) / sample_rate
        phase = ((i - pad) % cycle) / cycle
        envelope = .48 + .42 * sin(2 * pi * phase)
        click = 4700 * (1 - phase * 180) if phase < 1 / 180 else 0
        pcm.extend((round(10500 * envelope * sin(2 * pi * 150 * time) + click),
                    round(9000 * envelope * sin(2 * pi * 210 * time + .6) - click / 3)))
    artwork = (dict(start=12, end=68, overlap=6, offset=pad) if alternate
               else dict(start=6, end=63, overlap=5, offset=0))
    return encode_y4m(video, frames), encode_wav(Audio(sample_rate, 2, pcm)), artwork
