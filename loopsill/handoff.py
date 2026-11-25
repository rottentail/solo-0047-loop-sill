from io import BytesIO
from zipfile import ZIP_STORED, ZipFile, ZipInfo

from .identity import digest, identity, json_bytes
from .pcm import encode_wav
from .y4m import encode_y4m

PICTURE = 'cycle.y4m'
SOUND = 'cycle.wav'
MANIFEST = 'sill.json'
SCHEMA_VERSION = 1


def archive(members):
    output = BytesIO()
    with ZipFile(output, 'w') as bundle:
        for name, payload in sorted(members.items()):
            info = ZipInfo(name)
            info.compress_type = ZIP_STORED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            bundle.writestr(info, payload)
    return output.getvalue()


def make_handoff(capture, selection, revision, preview):
    members = {PICTURE: encode_y4m(capture.video, preview.picture), SOUND: encode_wav(preview.audio)}
    manifest = dict(version=SCHEMA_VERSION, source=capture.facts(), selection=selection.record(),
                    revision=revision, output=preview.record(capture.video),
                    members={name: dict(sha256=digest(data), size=len(data)) for name, data in members.items()})
    manifest['id'] = identity(manifest)
    members[MANIFEST] = json_bytes(manifest)
    blob = archive(members)
    return dict(id=manifest['id'], capture_id=capture.id, revision=revision,
                frame_count=len(preview.picture), sample_count=preview.audio.frames,
                bytes=len(blob), sha256=digest(blob)), blob
