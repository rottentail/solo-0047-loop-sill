from .errors import MediaError, integer
from .limits import MAX_SCAN_RADIUS
from .metrics import measure
from .selection import interpret


def scan(capture, selection, radius, focus):
    radius = integer(radius, '搜索半径', 1, MAX_SCAN_RADIUS)
    weights = {'balanced': (1, 1), 'picture': (3, 1), 'sound': (1, 3)}
    if not isinstance(focus, str) or focus not in weights:
        raise MediaError('候选优先项无效')
    pw, sw = weights[focus]
    candidates = []
    omitted = 0
    for delta in range(-radius, radius + 1):
        raw = selection.record()
        raw.update(start=selection.start + delta, end=selection.end + delta)
        try:
            proposed = interpret(capture, raw)
        except MediaError:
            omitted += 1
            continue
        evidence = measure(capture, proposed)
        audio_cost = max((channel['jump'] + channel['window_rms']) / 2 for channel in evidence['channels'])
        cost = (pw * evidence['luma'] + sw * audio_cost) / (pw + sw)
        candidates.append(dict(selection=proposed.record(), evidence=evidence, delta=delta, cost=cost))
    candidates.sort(key=lambda item: (item['cost'], abs(item['delta']), item['delta']))
    return dict(rows=candidates[:8], eligible=len(candidates), omitted=omitted)
