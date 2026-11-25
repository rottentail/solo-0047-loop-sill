from dataclasses import dataclass
from fractions import Fraction


def nearest(numerator, denominator):
    """最近整数，中点向正方向；分母为正。"""
    return (2 * numerator + denominator) // (2 * denominator)


@dataclass(frozen=True)
class Clock:
    rate: Fraction
    sample_rate: int
    offset: int = 0

    def sample(self, frame):
        return nearest(frame * self.sample_rate * self.rate.denominator, self.rate.numerator) + self.offset

    def span(self, frame):
        return self.sample(frame), self.sample(frame + 1)

    def boundaries(self, frames):
        return tuple(self.sample(i) for i in range(frames + 1))


def duration(rate, frames):
    value = Fraction(frames, 1) / rate
    return [value.numerator, value.denominator]
