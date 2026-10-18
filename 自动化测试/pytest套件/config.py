# -*- coding: utf-8 -*-
"""
项目配置。

被测对象：wagtail/bakerydemo（Wagtail 官方演示站点）
本项目只测**前台**（游客视角），不需要登录后台。
"""

import os
from pathlib import Path

ROOT = Path(__file__).parent

# 被测网站地址（默认本地，可用环境变量 BASE_URL 覆盖）
BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8000").rstrip("/") + "/"

# 失败截图目录
SCREENSHOT_DIR = ROOT / "截图"


def url(path=""):
    """拼完整网址：url('breads/') -> http://127.0.0.1:8000/breads/"""
    return BASE_URL + path.lstrip("/")
