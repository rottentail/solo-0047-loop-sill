from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.error import HTTPError
from urllib.request import urlopen
from threading import Thread
import struct
import wave

from .clock import Clock
from .demos import demo_capture
from .errors import MediaError
from .handoff import PICTURE, archive
from .offline import open_handoff, rehearse
from .server import ProjectionServer
from .verify import read_members
from .workbench import Workbench


def require(condition, message):
    if not condition:
        raise MediaError(f'流程检查失败：{message}')


def rejects(action, status):
    try:
        action()
    except (MediaError, HTTPError) as error:
        code = error.status if isinstance(error, MediaError) else error.code
        require(code == status, f'预期拒绝 {status}，实际 {code}')
        return str(error)
    raise MediaError('流程检查失败：未拒绝无效操作')


def ingest(app, _root, item):
    picture, sound, _ = demo_capture('counterbeat')
    repeated = app.register('配对副本', picture, sound)
    error = rejects(lambda: app.register('截断素材', picture[:-1], sound), 400)
    require(repeated['id'] == item['id'] and len(app.store.captures()) == 1, '相同原始字节须复用登记')
    return dict(capture=item['id'], fps=item['fps'], samples=item['sample_count'], error=error)


def measurement(app, _root, item):
    case = item['suggested']
    evidence = app.measure(item['id'], case)
    error = rejects(lambda: app.measure(item['id'], dict(case, start=0, offset=-1)), 422)
    require(len(evidence['channels']) == 2 and evidence['first_sample'] != case['offset'], '读数须保留逐声道与有理时钟')
    return dict(evidence=evidence, error=error)


def search(app, _root, item):
    case = dict(item['suggested'], start=0, end=56)
    result = app.scan(item['id'], case, 8, 'sound')
    rejects(lambda: app.scan(item['id'], case, 25, 'sound'), 400)
    require(result['omitted'] == 8 and result['eligible'] == 9, '移动不得越过来源范围')
    rows = result['rows']
    require(all(row['selection']['end'] - row['selection']['start'] == 56 for row in rows), '搜索须保持原跨度')
    require(sorted(row['cost'] for row in rows) == [row['cost'] for row in rows], '搜索结果按差异排序')
    return dict(eligible=result['eligible'], omitted=result['omitted'], best=rows[0])


def save(app, _root, item):
    key, choice = item['id'], item['suggested']
    first = app.save(key, choice, 0)
    second = app.save(key, dict(choice, overlap=0), first['revision'])
    error = rejects(lambda: app.save(key, choice, 1), 409)
    require(app.store.draft(key, 1) == choice and len(app.store.drafts(key)) == 2, '冲突时旧稿与最新稿保持完整')
    return dict(current=second, previous=first, error=error)


def inspect(app, _root, item):
    key, choice = item['id'], item['suggested']
    preview = app.source_frame(key, choice['start'])
    peaks = app.waveform(key, choice, 32)
    rejects(lambda: app.source_frame(key, item['frame_count']), 400)
    width, height = struct.unpack_from('>II', preview, 16)
    require(width > 0 and height > 0 and len(peaks['peaks']) == 2 and len(peaks['peaks'][0]) == 32, '画格像素和双声道波形须可查看')
    return dict(width=width, height=height, samples=[peaks['first_sample'], peaks['end_sample']], first_peaks=[row[0] for row in peaks['peaks']])


def preview(app, _root, item):
    key, choice = item['id'], item['suggested']
    info = app.preview_info(key, choice)
    flattened = app.preview_info(key, dict(choice, overlap=0))
    plan = info['plan']
    picture = app.preview_sheet(key, choice, 0)
    rejects(lambda: app.preview_sheet(key, choice, info['atlas']['sheets']), 400)
    require(plan['frame_count'] == choice['end'] - choice['start'] - choice['overlap'], '交叠格只压一次')
    require(plan['frame_count'] < flattened['plan']['frame_count'] and plan['frames'][-1]['head'] is not None, '交叠改变输出坐标并保留来源映射')
    require(plan['boundaries'][-1] == app.preview(key, choice).audio.frames and picture.startswith(b'\x89PNG'), '同一计划应物化声音和画面')
    return dict(frame_count=plan['frame_count'], sample_count=plan['sample_count'], last_frame=plan['frames'][-1], before=info['before'], after=info['after'])


def sealed(app, item):
    key = item['id']
    first = app.save(key, item['suggested'], 0)
    return app.freeze(key, first['revision'])


def freeze(app, _root, item):
    summary = sealed(app, item)
    key = item['id']
    app.save(key, dict(item['suggested'], overlap=0), 1)
    require(app.freeze(key, 1) == summary and len(app.store.handoffs(key)) == 1, '更新草稿不能改写第一次封存的结果')
    rejects(lambda: app.freeze(key, 3), 404)
    return summary


def download(app, root, item):
    summary = sealed(app, item)
    reopened = Workbench(root)
    with ProjectionServer(('127.0.0.1', 0), reopened) as server:
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            base = f'http://127.0.0.1:{server.server_port}/api/handoffs/'
            with urlopen(base + summary['id'], timeout=5) as response:
                blob = response.read()
                require(response.headers['Content-Type'] == 'application/zip' and blob == app.store.handoff(summary['id'])[1], '重开工位后下载字节须一致')
            rejects(lambda: urlopen(base + '0' * 64, timeout=5), 404)
        finally:
            server.shutdown()
            thread.join()
    return dict(revision=summary['revision'], bytes=len(blob), sha256=summary['sha256'])


def capture_bundle(app, root, item):
    summary = sealed(app, item)
    path = Path(root) / 'cycle.zip'
    path.write_bytes(app.store.handoff(summary['id'])[1])
    return path, summary


def verify(app, root, item):
    path, summary = capture_bundle(app, root, item)
    manifest, video, audio = open_handoff(path)
    members = read_members(path.read_bytes())
    members[PICTURE] = members[PICTURE][:-1]
    path.write_bytes(archive(members))
    error = rejects(lambda: open_handoff(path), 400)
    require(manifest['id'] == summary['id'] and len(video.frames) == summary['frame_count'] and audio.frames == summary['sample_count'], '接收端须独立读出成片时钟')
    return dict(id=summary['id'], frames=len(video.frames), samples=audio.frames, error=error)


def rehearsal(app, root, item):
    path, summary = capture_bundle(app, root, item)
    output = Path(root) / 'rehearsal'
    data = rehearse(path, output, 9)
    _, video, audio = open_handoff(path)
    clock = Clock(video.rate, audio.sample_rate)
    with wave.open(str(output / 'rehearsal.wav'), 'rb') as stream:
        require(stream.getnframes() == clock.sample(len(video.frames) * 9) == data['sample_count'], '实际多圈拾音须落在统一画格时钟')
    require(data['sample_count'] != summary['sample_count'] * 9, '有理帧率演示须区分逐圈舍入与绝对边界')
    rejects(lambda: rehearse(path, Path(root) / 'excess', 97), 400)
    return data


FLOWS = dict(ingest=ingest, measure=measurement, scan=search, save=save, inspect=inspect,
             preview=preview, freeze=freeze, download=download, verify=verify, rehearse=rehearsal)


def exercise(name):
    with TemporaryDirectory(prefix='loopsill-walkthrough-') as root:
        app = Workbench(root)
        item = app.demo('counterbeat')
        report = FLOWS[name](app, root, item)
        return dict(workflow=name, result=report)
