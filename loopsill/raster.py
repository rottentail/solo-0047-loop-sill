from .png import encode_png

TILE_MAX_WIDTH = 192
TILE_MAX_HEIGHT = 108
COLUMNS = 6
SHEET_FRAMES = 36


def tile_dimensions(video):
    width = min(video.width, TILE_MAX_WIDTH, video.width * TILE_MAX_HEIGHT // video.height)
    return width, max(1, width * video.height // video.width)


def clamp(value):
    return min(255, max(0, value))


def raster(video, frame, width, height):
    source_width, source_height = video.width, video.height
    luma_size = video.plane_size
    chroma_size = luma_size // 4
    buf = bytearray()
    xs = [x * source_width // width for x in range(width)]
    for y in range(height):
        sy = y * source_height // height
        row = sy * source_width
        chroma_row = sy // 2 * (source_width // 2)
        for sx in xs:
            chroma = chroma_row + sx // 2
            yy = 298 * (frame[row + sx] - 16)
            u = frame[luma_size + chroma] - 128
            v = frame[luma_size + chroma_size + chroma] - 128
            buf.extend((clamp((yy + 409 * v + 128) >> 8), clamp((yy - 100 * u - 208 * v + 128) >> 8),
                        clamp((yy + 516 * u + 128) >> 8)))
    return bytes(buf)


def frame_png(video, frame):
    width, height = tile_dimensions(video)
    return encode_png(width, height, raster(video, frame, width, height))


def atlas_info(video, count):
    width, height = tile_dimensions(video)
    return dict(tile_width=width, tile_height=height, columns=COLUMNS, per_sheet=SHEET_FRAMES,
                sheets=(count + SHEET_FRAMES - 1) // SHEET_FRAMES)


def atlas_png(video, frames, sheet):
    width, height = tile_dimensions(video)
    tiles = frames[sheet * SHEET_FRAMES:(sheet + 1) * SHEET_FRAMES]
    stride = COLUMNS * width * 3
    rows = (len(tiles) + COLUMNS - 1) // COLUMNS
    buf = bytearray(stride * height * rows)
    for index, frame in enumerate(tiles):
        rgb = raster(video, frame, width, height)
        column, row = index % COLUMNS, index // COLUMNS
        for y in range(height):
            start = ((row * height + y) * stride) + column * width * 3
            buf[start:start + width * 3] = rgb[y * width * 3:(y + 1) * width * 3]
    return encode_png(COLUMNS * width, rows * height, bytes(buf))
