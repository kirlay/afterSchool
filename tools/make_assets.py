# -*- coding: utf-8 -*-
"""开发期工具：从 xb.ico 生成屏幕 logo（logo.png）。

运行环境只需要 Pillow（开发机），打包出来的 exe 不依赖 Pillow。
用法：python tools/make_assets.py
"""
import os
import sys

try:
    from PIL import Image
except ImportError:
    sys.exit("需要 Pillow：python -m pip install pillow")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ICO = os.path.join(ROOT, "xb.ico")
PNG = os.path.join(ROOT, "logo.png")
LOGO_SIZE = 60


def main():
    if not os.path.exists(ICO):
        sys.exit("找不到 %s" % ICO)

    img = Image.open(ICO)
    sizes = sorted(img.ico.sizes()) if hasattr(img, "ico") else [img.size]
    img.size = sizes[-1]
    img = img.convert("RGBA")
    img.load()

    resample = getattr(Image, "Resampling", Image).LANCZOS
    logo = img.resize((LOGO_SIZE, LOGO_SIZE), resample)
    logo.save(PNG, "PNG")
    print("已生成 %s（源尺寸 %s，输出 %dx%d）" % (PNG, sizes[-1], LOGO_SIZE, LOGO_SIZE))


if __name__ == "__main__":
    main()
