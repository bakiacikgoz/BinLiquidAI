Generated Windows runtime bundle for AegisOS Operator Panel.

Release gate:
1) python/Scripts/python.exe exists
2) python/Scripts/python.exe -m binliquid --version passes
3) RUNTIME_MANIFEST.txt records platform, arch, Python entrypoint, source wheel, hashes, and git evidence

Do not ship placeholder-only runtime contents.
