# -*- coding: utf-8 -*-
"""
pytest 全局配置与夹具。

本项目测的是前台（游客视角），所以**不需要登录**，
夹具比上一个项目简单很多。
"""

import sys
import urllib.request
from pathlib import Path

import pytest

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from config import BASE_URL, SCREENSHOT_DIR  # noqa: E402


# ===========================================================================
# 钩子：记录每条用例的结果，供「失败自动截图」使用
# ===========================================================================
@pytest.hookimpl(wrapper=True)
def pytest_runtest_makereport(item, call):
    report = yield
    setattr(item, f"rep_{report.when}", report)
    return report


# ===========================================================================
# 夹具：开跑前检查网站是否可访问
# ===========================================================================
@pytest.fixture(scope="session", autouse=True)
def check_site_available():
    """连不上网站就立刻停下，并给出中文提示。"""
    try:
        urllib.request.urlopen(BASE_URL, timeout=10)
    except Exception as exc:
        pytest.exit(
            f"\n\n❌ 连不上被测网站：{BASE_URL}\n"
            f"   原因：{exc}\n\n"
            f"   请先启动 bakerydemo：\n"
            f"     cd C:\\AI文件夹\\bakerydemo\n"
            f"     .venv\\Scripts\\Activate.ps1\n"
            f"     python manage.py runserver\n",
            returncode=1,
        )


# ===========================================================================
# 夹具：浏览器 + 页面
# ===========================================================================
@pytest.fixture(scope="session")
def 浏览器():
    """整个测试只开一次浏览器"""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        yield browser
        browser.close()


@pytest.fixture
def 页面(浏览器, request):
    """
    一个干净的页面。每条用例独立，互不影响。

    默认无头模式（不弹窗口，跑得快）。
    想看着它操作：pytest --headed
    """
    context = 浏览器.new_context()
    page = context.new_page()
    page.set_default_timeout(15000)
    yield page

    # 用例失败时自动截图
    rep = getattr(request.node, "rep_call", None)
    if rep is not None and rep.failed:
        SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
        try:
            page.screenshot(path=str(SCREENSHOT_DIR / f"{request.node.name}.png"),
                            full_page=True)
        except Exception:
            pass

    context.close()
