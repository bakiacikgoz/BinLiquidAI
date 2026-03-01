from __future__ import annotations

import argparse
import json
from random import Random


def run(bits: int, seed: int) -> dict[str, object]:
    rng = Random(seed)
    spikes = [rng.choice([0, 1]) for _ in range(bits)]
    density = sum(spikes) / max(bits, 1)
    embedding = [round((value * 2 - 1) * 0.125, 4) for value in spikes]
    return {
        "seed": seed,
        "bits": bits,
        "spikes": spikes,
        "density": round(density, 4),
        "embedding_preview": embedding[:8],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Toy spike bridge generator")
    parser.add_argument("--bits", type=int, default=16)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    print(json.dumps(run(bits=args.bits, seed=args.seed), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
