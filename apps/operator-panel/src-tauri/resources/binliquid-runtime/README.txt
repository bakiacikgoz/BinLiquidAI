Generated runtime bundle location for ImperaOS Operator Console.

Release gate:
1) python/bin/python is executable on macOS bundles
2) python/bin/python -m binliquid --version passes
3) RUNTIME_MANIFEST.txt records platform, arch, Python version, BinLiquid version, wheel hash, git evidence, and build time

Do not ship placeholder-only runtime contents.
