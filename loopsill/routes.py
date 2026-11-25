from pathlib import Path
from mimetypes import guess_type

from .errors import MediaError, object_fields
from .identity import json_bytes, valid_id
from .pcm import encode_wav
from .request import path_number

WEB = Path(__file__).with_name('web')


def result(data, status=200):
    return status, 'application/json; charset=utf-8', json_bytes(data), {}


def media(data, content_type, headers=None):
    return 200, content_type, data, headers or {}


def get(app, req):
    if req.path == '/':
        return media((WEB / 'index.html').read_bytes(), 'text/html; charset=utf-8')
    parts = req.segments
    if len(parts) == 2 and parts[0] == 'static':
        path = WEB / parts[1]
        if path.suffix in ('.css', '.js') and path.is_file():
            return media(path.read_bytes(), guess_type(path.name)[0] or 'text/javascript')
    if parts == ['api', 'captures']:
        return result(app.store.captures())
    if len(parts) == 3 and parts[:2] == ['api', 'handoffs']:
        summary, blob = app.store.handoff(valid_id(parts[2]))
        return media(blob, 'application/zip', {'Content-Disposition': f'attachment; filename="loop-{summary["id"][:12]}.zip"'})
    if len(parts) >= 3 and parts[:2] == ['api', 'captures']:
        key, *route = parts[2:]
        valid_id(key)
        if not route:
            return result(app.store.capture_info(key))
        if route == ['drafts']:
            return result(app.store.drafts(key))
        if route == ['handoffs']:
            return result(app.store.handoffs(key))
        if len(route) == 2 and route[0] == 'frame':
            return media(app.source_frame(key, path_number(route[1])), 'image/png')
        if route == ['preview', 'audio']:
            return media(encode_wav(app.preview(key, req.selection()).audio), 'audio/wav')
        if len(route) == 3 and route[:2] == ['preview', 'sheet']:
            return media(app.preview_sheet(key, req.selection(), path_number(route[2])), 'image/png')
    raise MediaError('地址不存在', status=404)


def post(app, req):
    parts = req.segments
    if parts == ['api', 'captures']:
        return result(app.register(req.param('label'), *req.upload()), 201)
    if len(parts) == 3 and parts[:2] == ['api', 'demos']:
        return result(app.demo(parts[2]), 201)
    if len(parts) == 4 and parts[:2] == ['api', 'captures']:
        key, mode = parts[2:]
        valid_id(key)
        if mode == 'measure':
            return result(app.measure(key, req.json()))
        if mode == 'scan':
            body = object_fields(req.json(), ('selection', 'radius', 'focus'))
            return result(app.scan(key, body['selection'], body['radius'], body['focus']))
        if mode == 'waveform':
            body = object_fields(req.json(), ('selection', 'bins'))
            return result(app.waveform(key, body['selection'], body['bins']))
        if mode == 'preview':
            return result(app.preview_info(key, req.json()))
        if mode == 'drafts':
            body = object_fields(req.json(), ('selection', 'expected'))
            return result(app.save(key, body['selection'], body['expected']), 201)
        if mode == 'handoffs':
            body = object_fields(req.json(), ('revision',))
            return result(app.freeze(key, body['revision']), 201)
    raise MediaError('地址不存在', status=404)
