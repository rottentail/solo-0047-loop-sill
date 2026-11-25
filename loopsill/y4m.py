from dataclasses import dataclass
from fractions import Fraction
from io import BytesIO

from .errors import MediaError
from .limits import MAX_FRAMES, MAX_HEIGHT, MAX_SECONDS, MAX_VIDEO_BYTES, MAX_WIDTH


@dataclass(frozen=True)
class Video:
    width: int
    height: int
    rate: Fraction
    frames: tuple[bytes, ...]

    @property
    def plane_size(self):
        return self.width * self.height


def parse_y4m(data, *, minimum=4):
    if len(data) > MAX_VIDEO_BYTES:
        raise MediaError('画面文件超过大小上限', status=413)
    stream = BytesIO(data)
    line = stream.readline(1025)
    if not line.startswith(b'YUV4MPEG2 ') or not line.endswith(b'\n') or len(line) > 1024:
        raise MediaError('画面须有有效的 Y4M 流头')
    try:
        fields = {}
        for tag in line.decode('ascii').split()[1:]:
            key, value = tag[0], tag[1:]
            if key not in 'WHFICAX' or not value or (key in fields and key != 'X'):
                raise ValueError
            if key == 'X' and value.startswith('COLORRANGE=') and value != 'COLORRANGE=LIMITED':
                raise ValueError
            fields[key] = value
        width, height = int(fields['W']), int(fields['H'])
        num, den = map(int, fields['F'].split(':'))
        if not 1 <= num <= 120000 or not 1 <= den <= 10000:
            raise ValueError
        rate = Fraction(num, den)
        if fields.get('I') != 'p' or fields.get('C', '420jpeg') not in ('420', '420jpeg'):
            raise ValueError
        if fields.get('A', '0:0') not in ('0:0', '1:1'):
            raise ValueError
        if not (16 <= width <= MAX_WIDTH and 16 <= height <= MAX_HEIGHT and width % 2 == height % 2 == 0 and 1 <= rate <= 60):
            raise ValueError
    except (KeyError, ValueError, UnicodeError) as exc:
        raise MediaError('画面须为逐行 8 位 4:2:0 JPEG Y4M，使用方形像素和合法尺寸帧率') from exc
    frame_size = width * height * 3 // 2
    frames = []
    while header := stream.readline(129):
        if header != b'FRAME\n':
            raise MediaError('Y4M 画格头须为无扩展参数的 FRAME')
        pixels = stream.read(frame_size)
        if len(pixels) != frame_size:
            raise MediaError('Y4M 最后一格的像素数据不完整')
        frames.append(pixels)
        if len(frames) > MAX_FRAMES or len(frames) > MAX_SECONDS * rate:
            raise MediaError('画面超过画格或时长上限', status=413)
    if len(frames) < minimum:
        raise MediaError(f'画面至少需要 {minimum} 格')
    return Video(width, height, rate, tuple(frames))


def encode_y4m(video, frames):
    rate = video.rate
    header = f'YUV4MPEG2 W{video.width} H{video.height} F{rate.numerator}:{rate.denominator} Ip A1:1 C420jpeg\n'
    output = BytesIO()
    output.write(header.encode('ascii'))
    for pixels in frames:
        output.write(b'FRAME\n')
        output.write(pixels)
    return output.getvalue()
