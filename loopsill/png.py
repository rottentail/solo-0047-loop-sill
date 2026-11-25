import struct
from zlib import compress, crc32


def chunk(kind, data):
    return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', crc32(kind + data))


def encode_png(width, height, rgb):
    stride = width * 3
    scanlines = b''.join(b'\0' + rgb[i:i + stride] for i in range(0, len(rgb), stride))
    header = struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0)
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', header) + chunk(b'IDAT', compress(scanlines, 3)) + chunk(b'IEND', b'')
