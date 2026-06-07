class FeistelPermuter:
    """Class that shuffles numbers in a range, from 0 to 2**bits."""

    def __init__(self, seed: int, rounds: int, bits: int) -> None:
        self.seed = seed
        self.rounds = rounds
        self.bits = bits
        self.half_bits = bits // 2
        self.mask = (1 << self.half_bits) - 1
        self.full_mask = (1 << bits) - 1

    def random_index(self, x: int) -> int:
        lo = x & self.mask
        r = (x >> self.half_bits) & self.mask

        for i in range(self.rounds):
            nl = r
            f = ((r * 11 + (r >> 5) + self.seed + i * 127) ^ r) & self.mask
            r = lo ^ f
            lo = nl

        return ((r << self.half_bits) | lo) & self.full_mask
