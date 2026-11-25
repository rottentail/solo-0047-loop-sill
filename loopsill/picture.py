from .clock import nearest


def render_picture(video, plan):
    for shot in plan.shots:
        left = video.frames[shot.tail]
        if shot.head is None:
            yield left
            continue
        right = video.frames[shot.head]
        head_weight = 2 * shot.blend_index + 1
        scale = 2 * plan.overlap
        tail_weight = scale - head_weight
        yield bytes(nearest(a * tail_weight + b * head_weight, scale) for a, b in zip(left, right))


def luma_difference(first, second, width, height):
    stride = max(1, min(width, height) // 64)
    total = 0
    count = 0
    for y in range(0, height, stride):
        for x in range(0, width, stride):
            index = y * width + x
            total += abs(first[index] - second[index])
            count += 1
    return total / (255 * count)
