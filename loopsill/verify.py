from fractions import Fraction
from io import BytesIO
from types import SimpleNamespace
from zipfile import BadZipFile, ZIP_STORED, ZipFile
import json

from .errors import MediaError, integer, object_fields
from .handoff import MANIFEST, PICTURE, SCHEMA_VERSION, SOUND
from .identity import digest, identity, json_bytes, valid_id
from .limits import MAX_BUNDLE_BYTES, MAX_FRAMES
from .metrics import boundary
from .pcm import parse_wav
from .plan import make_plan
from .selection import interpret
from .y4m import parse_y4m


def read_members(blob):
    if len(blob) > MAX_BUNDLE_BYTES:
        raise MediaError('环带文件超过大小上限', status=413)
    try:
        with ZipFile(BytesIO(blob), 'r') as bundle:
            entries = bundle.infolist()
            if len(entries) != 3 or {i.filename for i in entries} != {MANIFEST, PICTURE, SOUND}:
                raise MediaError('环带成员集合不符')
            for item in entries:
                if item.compress_type != ZIP_STORED or item.flag_bits & 1 or item.file_size != item.compress_size:
                    raise MediaError('环带成员必须为未加密的存储成员')
            if sum(i.file_size for i in entries) > len(blob):
                raise MediaError('环带成员长度不符')
            if bundle.getinfo(MANIFEST).file_size > 64 * 1024:
                raise MediaError('环带清单过大')
            return {i.filename: bundle.read(i) for i in entries}
    except (BadZipFile, RuntimeError, OSError, NotImplementedError) as exc:
        raise MediaError('环带文件损坏或读取失败') from exc


def verify_handoff(blob):
    entries = read_members(blob)
    try:
        manifest = json.loads(entries[MANIFEST])
        object_fields(manifest, ('id', 'version', 'source', 'selection', 'revision', 'output', 'members'))
        manifest_id = manifest.pop('id')
        if type(manifest['version']) is not int or manifest['version'] != SCHEMA_VERSION or identity(manifest) != manifest_id:
            raise MediaError('环带版本或内容编号不符')
        manifest['id'] = manifest_id
        if json_bytes(manifest) != entries[MANIFEST]:
            raise MediaError('环带清单未采用约定编码')
        integer(manifest['revision'], '接缝稿编号', 1, 2 ** 31 - 1)
        object_fields(manifest['members'], (PICTURE, SOUND))
        for name in (PICTURE, SOUND):
            receipt = manifest['members'][name]
            if receipt != dict(size=len(entries[name]), sha256=digest(entries[name])):
                raise MediaError(f'{name} 的字节摘要不符')
        video, audio = parse_y4m(entries[PICTURE], minimum=3), parse_wav(entries[SOUND])
        verify_facts(manifest, video, audio)
        return manifest, video, audio
    except (UnicodeError, TypeError, KeyError, OverflowError, RecursionError) as exc:
        raise MediaError('环带清单字段无效') from exc
    except ValueError as exc:
        if isinstance(exc, MediaError):
            raise
        raise MediaError('环带清单字段无效') from exc


def verify_facts(manifest, video, audio):
    source = manifest['source']
    object_fields(source, ('id', 'video_sha256', 'audio_sha256', 'width', 'height', 'frame_count', 'fps',
                           'channels', 'sample_rate', 'sample_count'))
    source_id = identity([valid_id(source['video_sha256']), valid_id(source['audio_sha256'])])
    if source_id != source['id']:
        raise MediaError('来源配对编号不符')
    fps = [video.rate.numerator, video.rate.denominator]
    source_properties = (source['width'], source['height'], source['fps'], source['sample_rate'], source['channels'])
    if source_properties != (video.width, video.height, fps, audio.sample_rate, audio.channels):
        raise MediaError('成片解码事实与来源承诺不符')
    count = integer(source['frame_count'], '来源画格数', 4, MAX_FRAMES)
    audio_frames = integer(source['sample_count'], '来源样本数', 1, 30 * audio.sample_rate)
    capture = SimpleNamespace(video=SimpleNamespace(rate=Fraction(*fps), frames=range(count)),
                              audio=SimpleNamespace(sample_rate=audio.sample_rate, frames=audio_frames))
    selection = interpret(capture, manifest['selection'])
    plan = make_plan(capture, selection).record()
    after = boundary(video, audio, video.frames[0], video.frames[-1], 0, audio.frames)
    output = manifest['output']
    object_fields(output, ('id', 'plan', 'before', 'after', 'width', 'height', 'sample_rate', 'fps'))
    plan_matches = json_bytes(plan) == json_bytes(output['plan'])
    if not plan_matches or plan['frame_count'] != len(video.frames) or plan['sample_count'] != audio.frames:
        raise MediaError('成片画格或样本边界和清单不符')
    if (output['width'], output['height'], output['sample_rate'], output['fps']) != (video.width, video.height, audio.sample_rate, fps):
        raise MediaError('清单成片格式和解码结果不符')
    if output['id'] != identity([source_id, selection.record()]) or output['after'] != after:
        raise MediaError('成片编号或接缝读数不符')
