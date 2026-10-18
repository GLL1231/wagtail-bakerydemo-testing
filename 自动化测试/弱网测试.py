# -*- coding: utf-8 -*-
"""弱网与环境测试 —— 用 Playwright CDP 模拟 Slow 3G / 断网"""

import os
import sys
import time
from pathlib import Path

BAKERY = Path(r"C:\AI文件夹\bakerydemo")
VENV_PY = BAKERY / ".venv" / "Scripts" / "python.exe"
if VENV_PY.exists():
    try:
        if Path(sys.executable).resolve() != VENV_PY.resolve():
            os.execv(str(VENV_PY), [str(VENV_PY), os.path.abspath(__file__)] + sys.argv[1:])
    except Exception:
        pass

sys.path.insert(0, str(BAKERY))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "bakerydemo.settings.dev")
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"

import django  # noqa: E402

django.setup()

from playwright.sync_api import sync_playwright  # noqa: E402
from wagtail.contrib.forms.models import FormSubmission  # noqa: E402

BASE = "http://127.0.0.1:8000"

网络档位 = {
    "无边":   (0, -1),        # -1 = 不限速（CDP 规范）
    "Fast3G": (150, 1500),    # 150ms 延迟，1.5Mbps
    "Slow3G": (400, 400),     # 400ms 延迟，400kbps
}


def 设置网络(ctx, page, 档位="Slow3G", offline=False, cdp=None):
    """设置网络条件。传入已有的 cdp 会话可复用（避免旧设置残留）。"""
    if cdp is None:
        cdp = ctx.new_cdp_session(page)
        cdp.send("Network.enable")
    if offline:
        cdp.send("Network.emulateNetworkConditions", {
            "offline": True, "latency": 0,
            "downloadThroughput": 0, "uploadThroughput": 0})
    else:
        延迟, kbps = 网络档位[档位]
        吞吐 = -1 if kbps < 0 else kbps * 1024 // 8
        cdp.send("Network.emulateNetworkConditions", {
            "offline": False, "latency": 延迟,
            "downloadThroughput": 吞吐, "uploadThroughput": 吞吐})
    return cdp


def 新页面(browser, 档位="Slow3G"):
    ctx = browser.new_context()
    pg = ctx.new_page()
    pg.set_default_timeout(60000)
    pg.set_default_navigation_timeout(90000)
    设置网络(ctx, pg, 档位)
    return ctx, pg


def 计时加载(page, url, wait_until="domcontentloaded"):
    t0 = time.time()
    r = page.goto(url, wait_until=wait_until, timeout=90000)
    return round(time.time() - t0, 2), r


# ======================= 各条用例 =======================
def 弱网01(browser):
    ctx, pg = 新页面(browser, "Slow3G")
    try:
        耗时, r = 计时加载(pg, BASE + "/")
        h1 = pg.locator("h1").first.inner_text()
        return 耗时 < 15, f"HTTP {r.status}｜首屏耗时 {耗时}s｜H1={h1[:30]!r}（阈值 15s）"
    finally:
        ctx.close()


def 弱网02(browser):
    ctx, pg = 新页面(browser, "Slow3G")
    try:
        pg.goto(BASE + "/breads/", wait_until="domcontentloaded", timeout=90000)
        视口 = pg.evaluate("() => document.documentElement.clientWidth")
        早 = pg.evaluate("() => document.documentElement.scrollWidth")
        try:
            pg.wait_for_load_state("load", timeout=90000)
        except Exception:
            pass
        后 = pg.evaluate("() => document.documentElement.scrollWidth")
        return (早 <= 视口 + 1 and 后 <= 视口 + 1), \
            f"视口 {视口}px｜首屏时 {早}px｜完全加载后 {后}px"
    finally:
        ctx.close()


def 弱网03(browser):
    ctx, pg = 新页面(browser, "Slow3G")
    try:
        t0 = time.time()
        pg.goto(BASE + "/locations/reykjavik/", wait_until="domcontentloaded", timeout=90000)
        初始 = (pg.locator("location-status").first.inner_text() or "").strip()
        变化 = None
        for _ in range(30):
            pg.wait_for_timeout(500)
            now = (pg.locator("location-status").first.inner_text() or "").strip()
            if now != 初始:
                变化 = round(time.time() - t0, 1)
                break
        最终 = (pg.locator("location-status").first.inner_text() or "").strip()
        return ("Please wait" not in 最终), \
            f"初始={初始[:20]!r}｜{变化}s 后={最终[:50]!r}"
    finally:
        ctx.close()


def 弱网04(browser):
    ctx, pg = 新页面(browser, "Slow3G")
    前 = FormSubmission.objects.count()
    try:
        pg.goto(BASE + "/contact-us/", wait_until="domcontentloaded", timeout=90000)
        pg.fill("#id_subject", "弱网重复提交测试")
        pg.fill("#id_your_name", "测试员")
        pg.fill("#id_your_email", "test@example.com")
        pg.select_option("#id_purpose", index=1)
        pg.fill("#id_body", "弱网下连续点击提交按钮")
        try:
            pg.evaluate("""() => {
                const b = document.querySelector(
                    'form[action="/contact-us/"] input[type="submit"]');
                if (b) { for (let i = 0; i < 3; i++) b.click(); }
            }""")
        except Exception:
            pass
        pg.wait_for_timeout(20000)
        新增 = FormSubmission.objects.count() - 前
        return 新增 == 1, f"连点 3 次，实际新增 {新增} 条提交记录"
    finally:
        for s in FormSubmission.objects.filter(form_data__subject="弱网重复提交测试"):
            s.delete()
        ctx.close()


def 弱网05(browser):
    ctx, pg = 新页面(browser, "无边")
    try:
        pg.goto(BASE + "/", wait_until="domcontentloaded", timeout=90000)
        cdp = 设置网络(ctx, pg, offline=True)
        断网异常 = False
        try:
            pg.goto(BASE + "/breads/", wait_until="domcontentloaded", timeout=15000)
        except Exception:
            断网异常 = True
        # 复用同一个 cdp 会话恢复网络
        设置网络(ctx, pg, "无边", cdp=cdp)
        pg.wait_for_timeout(1000)
        r = pg.goto(BASE + "/breads/", wait_until="domcontentloaded", timeout=60000)
        卡片数 = pg.locator(".listing-card").count()
        return (r.status == 200 and 卡片数 > 0), (
            f"断网时导航{'失败（合理）' if 断网异常 else '未失败'}｜"
            f"恢复后 HTTP {r.status}，页面渲染出 {卡片数} 个面包卡片")
    finally:
        ctx.close()


def 弱网06(browser):
    表 = {}
    for 档 in ["无边", "Fast3G", "Slow3G"]:
        ctx, pg = 新页面(browser, 档)
        try:
            表[档], _ = 计时加载(pg, BASE + "/")
        finally:
            ctx.close()
    趋势 = 表["无边"] <= 表["Fast3G"] <= 表["Slow3G"]
    return 趋势, (f"无边 {表['无边']}s ≤ Fast3G {表['Fast3G']}s ≤ "
                  f"Slow3G {表['Slow3G']}s")


def 弱网07(browser):
    ctx, pg = 新页面(browser, "Slow3G")
    try:
        pg.goto(BASE + "/contact-us/", wait_until="domcontentloaded", timeout=90000)
        pg.fill("#id_subject", "保留测试")
        pg.fill("#id_your_name", "测试员")
        pg.fill("#id_your_email", "test@example.com")
        pg.select_option("#id_purpose", index=1)
        pg.fill("#id_body", "这段内容在提交过程中不应丢失")
        前 = pg.input_value("#id_body")
        try:
            pg.evaluate("""() => {
                const b = document.querySelector(
                    'form[action="/contact-us/"] input[type="submit"]');
                if (b) b.click();
            }""")
        except Exception:
            pass
        pg.wait_for_timeout(4000)
        try:
            后 = pg.input_value("#id_body") if pg.locator("#id_body").count() else None
        except Exception:
            后 = None
        return (后 is None or 后 == 前), \
            f"提交前={前[:15]!r}｜提交后={'已离开表单页' if 后 is None else 后[:15]!r}"
    finally:
        for s in FormSubmission.objects.filter(form_data__subject="保留测试"):
            s.delete()
        ctx.close()


用例 = [
    ("弱网-01", "Slow 3G 下首屏加载时间可接受", 弱网01),
    ("弱网-02", "弱网下布局稳定、无横向溢出", 弱网02),
    ("弱网-03", "弱网下营业状态组件的加载与最终状态", 弱网03),
    ("弱网-04", "弱网下重复点击提交不产生重复数据", 弱网04),
    ("弱网-05", "断网后恢复，页面能正常继续使用", 弱网05),
    ("弱网-06", "三种网络环境加载耗时呈合理趋势", 弱网06),
    ("弱网-07", "弱网下提交过程不丢失已填写内容", 弱网07),
]


def main():
    print("\n" + "=" * 70)
    print("  弱网与环境测试（CDP 模拟网络）")
    print("=" * 70)

    结果 = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        for 编号, 名称, 函数 in 用例:
            try:
                通过, 说明 = 函数(browser)
            except Exception as exc:  # noqa: BLE001
                通过, 说明 = False, f"执行异常 {type(exc).__name__}: {str(exc)[:110]}"
            结果.append((编号, 名称, 通过, 说明))
            print(f"  {'✅ 通过' if 通过 else '❌ 不通过'}  {编号}  {名称}")
            print(f"           {说明}")
        browser.close()

    通过数 = sum(1 for x in 结果 if x[2])
    print("\n" + "=" * 70)
    print(f"  结果：{通过数} / {len(结果)} 条通过")
    print("=" * 70)
    for 编号, 名称, 通过, 说明 in 结果:
        if not 通过:
            print(f"    ❌ {编号}  {名称}")
    print()
    return 结果


if __name__ == "__main__":
    main()
