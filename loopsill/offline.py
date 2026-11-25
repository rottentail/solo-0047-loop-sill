from pathlib import Path
from shutil import rmtree

from .errors import MediaError
from .identity import json_bytes
from .limits import MAX_BUNDLE_BYTES
from .pcm import encode_wav
from .repetition import repeat_samples
from .verify import verify_handoff
from .y4m import encode_y4m


def open_handoff(path):
    with Path(path).open('rb') as source:
        blob = source.read(MAX_BUNDLE_BYTES + 1)
    return verify_handoff(blob)


def rehearse(path, output, turns):
    manifest, video, audio = open_handoff(path)
    repeated, boundaries = repeat_samples(video, audio, turns)
    picture = (frame for _ in range(turns) for frame in video.frames)
    summary = dict(handoff=manifest['id'], turns=turns, turn_samples=boundaries,
                   frame_count=len(video.frames) * turns, fps=manifest['output']['fps'],
                   sample_rate=audio.sample_rate, sample_count=repeated.frames)
    output = Path(output)
    output.mkdir()
    try:
        (output / 'rehearsal.y4m').write_bytes(encode_y4m(video, picture))
        (output / 'rehearsal.wav').write_bytes(encode_wav(repeated))
        (output / 'rehearsal.json').write_bytes(json_bytes(summary) + b'\n')
    except OSError:
        rmtree(output)
        raise
    return summary


def export_demo(directory, kind):
    from .demos import demo_capture

    picture, sound, selection = demo_capture(kind)
    root = Path(directory)
    root.mkdir()
    try:
        (root / 'capture.y4m').write_bytes(picture)
        (root / 'capture.wav').write_bytes(sound)
        (root / 'selection.json').write_bytes(json_bytes(selection) + b'\n')
    except OSError:
        rmtree(root)
        raise
    return selection
