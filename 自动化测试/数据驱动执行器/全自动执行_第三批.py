# -*- coding: utf-8 -*-
"""第三批：版本回滚、版本历史、表单后台记录、表单 XSS、重复提交"""

import os
import sys
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

from bakerydemo.base.models import FormPage  # noqa: E402
from bakerydemo.breads.models import BreadPage  # noqa: E402

BASE = "http://127.0.0.1:8000"
表单页 = FormPage.objects.first()
提交地址 = f"/admin/forms/submissions/{表单页.pk}/"


def 提交表单(pg, subject, body, 邮箱="test@example.com"):
    pg.goto(BASE + "/contact-us/", wait_until="domcontentloaded", timeout=60000)
    pg.fill("#id_subject", subject)
    pg.fill("#id_your_name", "测试员")
    pg.fill("#id_your_email", 邮箱)
    pg.select_option("#id_purpose", index=1)
    pg.fill("#id_body", body)
    pg.locator('form[action="/contact-us/"] input[type="submit"]').first.click()
    pg.wait_for_load_state("domcontentloaded")


def 清理(subject):
    for s in FormSubmission.objects.filter(form_data__subject=subject):
        s.delete()


# ======================= 用例 =======================
def 版本01(browser):
    """回滚到旧版本后，前台显示旧内容"""
    p = BreadPage.objects.get(slug="anadama-bread")
    原 = p.title
    try:
        p.title = "版本A回滚测试"
        ra = p.save_revision(); ra.publish()
        p.title = "版本B回滚测试"
        rb = p.save_revision(); rb.publish()

        ctx = browser.new_context(); pg = ctx.new_page()
        try:
            pg.goto(BASE + "/breads/anadama-bread/", wait_until="domcontentloaded")
            pg.wait_for_timeout(400)
            改回前 = pg.locator("h1").first.inner_text().strip()

            ra.publish()          # 回滚到版本 A
            pg.reload(); pg.wait_for_timeout(400)
            回滚后 = pg.locator("h1").first.inner_text().strip()
            return (回滚后 == "版本A回滚测试"), \
                f"回滚前 H1={改回前!r}｜回滚后 H1={回滚后!r}"
        finally:
            ctx.close()
    finally:
        p.refresh_from_db()
        p.title = 原
        p.save_revision().publish()


def 版本03(browser):
    """版本历史能记录修改，条数随修改增加"""
    p = BreadPage.objects.get(slug="anadama-bread")
    原 = p.title
    前 = p.revisions.count()
    try:
        p.title = "版本历史测试"
        p.save_revision().publish()
        p.refresh_from_db()
        后 = p.revisions.count()
        # 检查每条都有时间和作者字段
        完整 = all(r.created_at is not None for r in p.revisions.all()[:5])
        return (后 == 前 + 1 and 完整), \
            f"修改前 {前} 个版本，修改后 {后} 个版本；时间字段完整={完整}"
    finally:
        p.refresh_from_db()
        p.title = 原
        p.save_revision().publish()


def 表单04(browser):
    """提交后后台能看到记录，内容一致"""
    主题 = "自动化-后台记录测试"
    内容 = "这条内容应该出现在后台表单记录里"
    前 = FormSubmission.objects.count()
    ctx = browser.new_context(); pg = ctx.new_page()
    try:
        提交表单(pg, 主题, 内容)
        pg.wait_for_timeout(500)
        后 = FormSubmission.objects.count()
        匹配 = FormSubmission.objects.filter(
            form_data__subject=主题, form_data__body=内容).exists()
        return (后 == 前 + 1 and 匹配), \
            f"提交前 {前} 条，提交后 {后} 条；后台记录内容匹配={匹配}"
    finally:
        清理(主题)
        ctx.close()


def 表单05(browser):
    """提交含脚本的内容，后台查看时不执行（存储型 XSS）"""
    主题 = "自动化-XSS测试"
    内容 = "<script>alert('XSS')</script>"
    前 = FormSubmission.objects.count()
    ctx = browser.new_context(); pg = ctx.new_page()
    try:
        提交表单(pg, 主题, 内容)
        pg.wait_for_timeout(500)
        已存 = FormSubmission.objects.filter(form_data__subject=主题).exists()

        # 登录后台，打开提交记录页，看有没有弹窗
        弹窗 = []
        pg.on("dialog", lambda d: (弹窗.append(d.message), d.dismiss()))

        pg.goto(BASE + "/admin/login/", wait_until="domcontentloaded")
        # Wagtail 后台登录
        pg.fill('input[name="username"]', "admin")
        pg.fill('input[name="password"]', "changeme")
        pg.locator('button[type="submit"]').first.click()
        pg.wait_for_load_state("domcontentloaded")
        pg.wait_for_timeout(1500)

        r = pg.goto(BASE + 提交地址, wait_until="domcontentloaded", timeout=60000)
        pg.wait_for_timeout(1200)

        return (已存 and not 弹窗 and r.status == 200), \
            (f"提交已存入={已存}｜后台提交记录页 HTTP {r.status}｜"
             f"触发弹窗={弹窗 if 弹窗 else '无'}")
    finally:
        清理(主题)
        ctx.close()


def 表单06(browser):
    """重复提交同一表单，记录数与提交次数一致（不出现异常重复）"""
    主题 = "自动化-重复提交测试"
    前 = FormSubmission.objects.count()
    ctx = browser.new_context(); pg = ctx.new_page()
    try:
        for i in range(3):
            提交表单(pg, 主题, f"第 {i+1} 次提交")
            pg.wait_for_timeout(400)
        后 = FormSubmission.objects.count()
        新增 = 后 - 前
        return (新增 == 3), \
            f"顺序提交 3 次，后台新增 {新增} 条记录（每次提交各一条，属正常）"
    finally:
        清理(主题)
        ctx.close()


用例 = [
    ("版本-01", "回滚到旧版本后前台恢复旧内容", 版本01),
    ("版本-03", "版本历史完整记录修改", 版本03),
    ("表单-04", "提交后后台能看到该条记录", 表单04),
    ("表单-05", "提交含脚本内容，后台查看时不执行", 表单05),
    ("表单-06", "重复提交不产生异常重复", 表单06),
]


def main():
    print("\n" + "=" * 70)
    print("  第三批自动化执行")
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
    return 结果


if __name__ == "__main__":
    main()
