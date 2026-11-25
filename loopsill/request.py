from urllib.parse import parse_qs, urlsplit
import json
import re
import struct

from .errors import MediaError
from .limits import MAX_AUDIO_BYTES, MAX_JSON_BYTES, MAX_VIDEO_BYTES


class Request:
    def __init__(self, handler):
        value = urlsplit(handler.path)
        self.handler = handler
        self.path = value.path
        self.segments = value.path.strip('/').split('/')
        try:
            self.query = parse_qs(value.query, keep_blank_values=True, max_num_fields=8)
        except ValueError as exc:
            raise MediaError('查询参数过多') from exc

    def param(self, key):
        values = self.query.get(key, [])
        if len(values) != 1:
            raise MediaError(f'查询项 {key} 缺失或重复')
        return values[0]

    def number(self, key):
        return path_number(self.param(key))

    def selection(self):
        if set(self.query) != {'start', 'end', 'overlap', 'offset'}:
            raise MediaError('预演选区字段不完整')
        return {key: self.number(key) for key in self.query}

    def body(self, content_type, limit):
        if self.handler.headers.get_content_type() != content_type:
            raise MediaError('请求内容类型不符', status=415)
        amounts = self.handler.headers.get_all('Content-Length', [])
        if self.handler.headers.get('Transfer-Encoding') or len(amounts) != 1 or not re.fullmatch(r'[0-9]{1,10}', amounts[0]):
            raise MediaError('需要有效的请求长度', status=411)
        amount = int(amounts[0])
        if amount > limit:
            raise MediaError('请求超过大小上限', status=413)
        payload = self.handler.rfile.read(amount)
        if len(payload) != amount:
            raise MediaError('请求未完整接收')
        return payload

    def json(self):
        try:
            return json.loads(self.body('application/json', MAX_JSON_BYTES).decode('utf-8'))
        except (json.JSONDecodeError, UnicodeError, RecursionError) as exc:
            raise MediaError('请求 JSON 无效') from exc

    def upload(self):
        payload = self.body('application/octet-stream', MAX_VIDEO_BYTES + MAX_AUDIO_BYTES + 4)
        if len(payload) < 6:
            raise MediaError('配对上传内容不完整')
        size, = struct.unpack_from('>I', payload)
        if not 0 < size < len(payload) - 4:
            raise MediaError('上传画面长度无效')
        return payload[4:4 + size], payload[4 + size:]


def path_number(value):
    if not re.fullmatch(r'-?[0-9]{1,10}', value):
        raise MediaError('编号或边界须为整数')
    return int(value)
