from array import array
from dataclasses import dataclass
from io import BytesIO
import struct
import wave

from .errors import MediaError
from .limits import MAX_AUDIO_BYTES, MAX_SECONDS


@dataclass(frozen=True)
class Audio:
    sample_rate: int
    channels: int
    pcm: array

    @property
    def frames(self):
        return len(self.pcm) // self.channels

    def sample(self, index, channel):
        return self.pcm[index * self.channels + channel]


def parse_wav(data):
    if len(data) > MAX_AUDIO_BYTES:
        raise MediaError('拾音文件超过大小上限', status=413)
    if len(data) < 44 or data[:4] != b'RIFF' or data[8:12] != b'WAVE' or struct.unpack_from('<I', data, 4)[0] + 8 != len(data):
        raise MediaError('WAV 容器长度与实际字节不一致')
    offset = 12
    data_size = None
    seen_format = False
    while offset + 8 <= len(data):
        kind, size = struct.unpack_from('<4sI', data, offset)
        offset += 8 + size + (size % 2)
        if offset > len(data):
            raise MediaError('WAV 数据块不完整')
        if kind == b'fmt ':
            if seen_format or data_size is not None:
                raise MediaError('WAV 格式块重复或顺序无效')
            seen_format = True
        if kind == b'data':
            if not seen_format or data_size is not None:
                raise MediaError('WAV 数据块重复或顺序无效')
            data_size = size
    if offset != len(data) or data_size is None:
        raise MediaError('WAV 缺少有效数据块')
    try:
        with wave.open(BytesIO(data), 'rb') as stream:
            rate, channels, length = stream.getframerate(), stream.getnchannels(), stream.getnframes()
            if stream.getsampwidth() != 2 or stream.getcomptype() != 'NONE' or channels not in (1, 2) or not 8000 <= rate <= 48000:
                raise MediaError('拾音须为 8–48 kHz、单声道或双声道的 16 位 PCM WAV')
            if not 0 < length <= rate * MAX_SECONDS or data_size != length * channels * 2:
                raise MediaError('WAV 样本数量或声道对齐无效')
            pcm = array('h')
            payload = stream.readframes(length)
            if len(payload) != data_size:
                raise MediaError('WAV 采样已截断')
            pcm.frombytes(payload)
            return Audio(rate, channels, pcm)
    except (wave.Error, EOFError, struct.error) as exc:
        raise MediaError('WAV 拾音格式无法读出') from exc


def encode_wav(audio):
    output = BytesIO()
    with wave.open(output, 'wb') as stream:
        stream.setparams((audio.channels, 2, audio.sample_rate, 0, 'NONE', 'not compressed'))
        stream.writeframes(audio.pcm.tobytes())
    return output.getvalue()
