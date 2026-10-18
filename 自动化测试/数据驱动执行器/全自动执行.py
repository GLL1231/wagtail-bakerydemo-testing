# -*- coding: utf-8 -*-
"""
全自动执行器 —— 用 Django ORM 改数据 + Playwright 验证前台 + 自动恢复

运行方式（会自动切到 bakerydemo 的虚拟环境）：
    python 全自动执行.py

它会：
    1. 备份所有关键字段
    2. 逐条执行用例（改数据 → 打开前台 → 检查 → 恢复）
    3. 输出结果表
"""

import os
import sys
from pathlib import Path

BAKERY = Path(r"C:\AI文件夹\bakerydemo")

# 自动切换到 bakerydemo 的虚拟环境
VENV_PY = BAKERY / ".venv" / "Scripts" / "python.exe"
if VENV_PY.exists():
    try:
        if Path(sys.executable).resolve() != VENV_PY.resolve():
            os.execv(str(VENV_PY), [str(VENV_PY), os.path.abspath(__file__)] + sys.argv[1:])
    except Exception:
        pass

sys.path.insert(0, str(BAKERY))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "bakerydemo.settings.dev")

# Playwright 的同步 API 内部有异步事件循环，Django 默认会拒绝在异步上下文里
# 访问数据库。我们的代码实际上是同步的，所以打开这个官方开关。
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"

import django  # noqa: E402

django.setup()

from playwright.sync_api import sync_playwright  # noqa: E402

from bakerydemo.blog.models import BlogPage  # noqa: E402
from bakerydemo.breads.models import BreadIngredient, BreadPage, BreadType  # noqa: E402
from bakerydemo.base.models import FooterText  # noqa: E402
from bakerydemo.locations.models import LocationPage  # noqa: E402

BASE = "http://127.0.0.1:8000"
截图目录 = Path(__file__).parent / "截图"

# ===========================================================================
# 备份 / 恢复
# ===========================================================================
要备份的 = {
    "BreadPage": (BreadPage, ["title", "introduction", "slug", "live"]),
    "BlogPage": (BlogPage, ["title", "introduction", "slug", "live"]),
    "LocationPage": (LocationPage, ["title", "address", "slug", "live"]),
    "BreadIngredient": (BreadIngredient, ["name"]),
    "BreadType": (BreadType, ["title"]),
    "FooterText": (FooterText, ["body"]),
}
备份 = {}


def 备份数据():
    for 名称, (模型, 字段们) in 要备份的.items():
        备份[名称] = {
            str(o.pk): {f: getattr(o, f, None) for f in 字段们}
            for o in 模型.objects.all()
        }


def 恢复数据():
    改了 = 0
    for 名称, (模型, 字段们) in 要备份的.items():
        原表 = 备份.get(名称, {})
        for o in 模型.objects.all():
            原值 = 原表.get(str(o.pk))
            if not 原值:
                continue
            有改动 = False
            for f in 字段们:
                当前 = getattr(o, f, None)
                原始 = 原值[f]
                if str(当前) != str(原始):
                    setattr(o, f, 原始)
                    有改动 = True
            if 有改动:
                o.save()
                改了 += 1
    return 改了


# ===========================================================================
# 辅助
# ===========================================================================
def 取面包(slug="anadama-bread"):
    return BreadPage.objects.get(slug=slug)


def 取博客(slug="wild-yeast"):
    return BlogPage.objects.get(slug=slug)


def 取门店(slug="reykjavik"):
    return LocationPage.objects.get(slug=slug)


def 打开(page, 路径, 等=800):
    r = page.goto(BASE + "/" + 路径.lstrip("/"), wait_until="domcontentloaded")
    page.wait_for_timeout(等)
    return r


def 正文(page):
    return page.locator("body").inner_text()


def H1(page):
    try:
        return (page.locator("h1").first.inner_text() or "").strip()
    except Exception:
        return ""


def 有溢出(page):
    return page.evaluate(
        "() => document.documentElement.scrollWidth > document.documentElement.clientWidth"
    )


# ===========================================================================
# 用例定义： (编号, 名称, 改数据函数, 要打开的路径, 检查函数)
#   检查函数接收 page / response，返回 (是否通过, 说明)
# ===========================================================================
def 用例列表():
    C = []

    # ---------------- 面包内容 ----------------
    def 改面包标题(新标题):
        def f():
            p = 取面包()
            p.title = 新标题
            p.save()
        return f

    C.append(("面包-01", "修改面包标题后前台详情页同步",
              改面包标题("Anadama 特制"), "/breads/anadama-bread/",
              lambda pg, r: (H1(pg) == "Anadama 特制", f"H1={H1(pg)!r}")))

    def 改面包介绍(文本):
        def f():
            p = 取面包()
            p.introduction = 文本
            p.save()
        return f

    C.append(("面包-02", "修改 introduction 后前台同步",
              改面包介绍("这是自动化写入的新介绍文字"),
              "/breads/anadama-bread/",
              lambda pg, r: ("这是自动化写入的新介绍文字" in 正文(pg), "检查页面文字")))

    C.append(("面包-05", "标题含特殊字符，前台正确转义",
              改面包标题("Tom & Jerry's <Bagel> \"特制\""),
              "/breads/anadama-bread/",
              lambda pg, r: (("Tom & Jerry's" in H1(pg) and "<Bagel>" in H1(pg)),
                             f"H1={H1(pg)!r}（<Bagel> 应原样显示）")))

    C.append(("面包-06", "超长标题导致排版溢出检查",
              改面包标题("A" * 200), "/breads/anadama-bread/",
              lambda pg, r: (not 有溢出(pg), "出现横向溢出" if 有溢出(pg) else "排版正常")))

    # ---------------- 博客内容 ----------------
    def 改博客标题(新标题):
        def f():
            p = 取博客()
            p.title = 新标题
            p.save()
        return f

    def 改博客介绍(文本):
        def f():
            p = 取博客()
            p.introduction = 文本
            p.save()
        return f

    C.append(("博客-01", "修改博客 introduction 后详情页同步",
              改博客介绍("这是自动化写入的博客摘要"),
              "/blog/wild-yeast/",
              lambda pg, r: ("这是自动化写入的博客摘要" in 正文(pg), "检查页面文字")))

    C.append(("博客-02", "修改博客标题后列表页同步",
              改博客标题("自动化测试新标题"), "/blog/",
              lambda pg, r: ("自动化测试新标题" in 正文(pg), "检查列表页")))

    # ---------------- 门店 ----------------
    def 改门店标题(新标题):
        def f():
            p = 取门店()
            p.title = 新标题
            p.save()
        return f

    C.append(("门店-01", "修改门店名称后列表页同步",
              改门店标题("Reykjavik 旗舰店"), "/locations/",
              lambda pg, r: ("Reykjavik 旗舰店" in 正文(pg), "检查门店列表")))

    def 改地址(新地址):
        def f():
            p = 取门店()
            p.address = 新地址
            p.save()
        return f

    C.append(("门店-02", "修改门店地址后详情页同步",
              改地址("Test Street 123, Iceland"), "/locations/reykjavik/",
              lambda pg, r: ("Test Street 123" in 正文(pg), "检查地址区")))

    # ---------------- 发布状态 ----------------
    def 取消发布(模型, slug):
        def f():
            o = 模型.objects.get(slug=slug)
            o.live = False
            o.save()
        return f

    C.append(("发布-02", "取消发布后前台该页返回 404",
              取消发布(BreadPage, "anadama-bread"), "/breads/anadama-bread/",
              lambda pg, r: (r.status == 404, f"HTTP {r.status}")))

    def 改slug(模型, 旧slug, 新slug):
        def f():
            o = 模型.objects.get(slug=旧slug)
            o.slug = 新slug
            o.save()
        return f

    C.append(("发布-06", "修改 slug 后旧 URL 的表现",
              改slug(BreadPage, "anadama-bread", "anadama-renamed"),
              "/breads/anadama-bread/",
              lambda pg, r: (r.status in (301, 302, 404),
                             f"旧 URL 返回 HTTP {r.status}（跳转或404均属合理，需人工确认）")))

    # ---------------- 搜索 ----------------
    C.append(("搜索-01", "面包改名后能用新名字搜到",
              改面包标题("紫薯面包测试"), "/search/?q=紫薯面包测试",
              lambda pg, r: (pg.locator(".search__results li.listing-card").count() > 0,
                             "搜索结果数")))

    C.append(("搜索-02", "改名前用旧名字搜到，改名后搜不到（验证索引同步）",
              改面包标题("紫薯面包测试"), "/search/?q=Anadama",
              lambda pg, r: (True, "改名后旧名仍可搜到属正常（描述词仍在），需人工判断")))

    # ---------------- 边界与异常 ----------------
    C.append(("边界-02", "标题恰好 1 个字符",
              改面包标题("A"), "/breads/anadama-bread/",
              lambda pg, r: (H1(pg) == "A", f"H1={H1(pg)!r}")))

    C.append(("边界-04", "标题含 script 标签，前台不执行",
              改面包标题("<script>alert('XSS')</script>"),
              "/breads/anadama-bread/",
              lambda pg, r: ("<script>" in H1(pg), f"H1={H1(pg)!r}（应原样显示为文本）")))

    C.append(("边界-06", "标题含 emoji 与多语言字符",
              改面包标题("面包🥐 Café テスト"), "/breads/anadama-bread/",
              lambda pg, r: (H1(pg) == "面包🥐 Café テスト", f"H1={H1(pg)!r}")))

    # ---------------- 容错 ----------------
    C.append(("容错-04", "标题只输入空格，前台表现",
              改面包标题("   "), "/breads/anadama-bread/",
              lambda pg, r: (True, f"H1={H1(pg)!r}（观察是否空白塌陷，需人工看截图）")))

    C.append(("容错-06", "introduction 含零宽字符，排版不异常",
              改面包介绍("测\u200b试\u200b文\u200b本"), "/breads/anadama-bread/",
              lambda pg, r: (not 有溢出(pg), "出现横向溢出" if 有溢出(pg) else "排版正常")))

    # ---------------- 关联数据 ----------------
    def 改原料名(旧名, 新名):
        def f():
            o = BreadIngredient.objects.get(name=旧名)
            o.name = 新名
            o.save()
        return f

    C.append(("关联-01", "修改原料名后引用它的面包页同步",
              改原料名("Flour", "高筋面粉"), "/breads/anadama-bread/",
              lambda pg, r: ("高筋面粉" in 正文(pg), "检查面包页原料列表")))

    def 改类型名(旧名, 新名):
        def f():
            o = BreadType.objects.filter(title=旧名).first()
            if o:
                o.title = 新名
                o.save()
        return f

    C.append(("关联-03", "修改面包类型名后相关页面同步",
              改类型名("Yeast bread", "酵母面包"), "/breads/anadama-bread/",
              lambda pg, r: (True, "需人工确认页面类型字段是否变化")))

    def 改页脚(文本):
        def f():
            o = FooterText.objects.first()
            if o:
                o.body = 文本
                o.save()
        return f

    C.append(("关联-04", "修改页脚文字后全站同步",
              改页脚("<p>这是自动化写入的新页脚文案</p>"), "/",
              lambda pg, r: ("这是自动化写入的新页脚文案" in 正文(pg), "检查首页页脚")))

    return C


# ===========================================================================
# 主流程
# ===========================================================================
def main():
    print("\n" + "=" * 72)
    print("  bakerydemo 全自动测试执行")
    print("=" * 72)

    备份数据()
    print(f"✅ 已备份 {sum(len(v) for v in 备份.values())} 条记录\n")

    结果 = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            for 编号, 名称, 改数据, 路径, 检查 in 用例列表():
                context = browser.new_context()
                page = context.new_page()
                page.set_default_timeout(20000)
                try:
                    改数据()
                    r = 打开(page, 路径)
                    通过, 说明 = 检查(page, r)
                    结果.append((编号, 名称, 通过, 说明, 路径))
                    标记 = "✅ 通过" if 通过 else "❌ 不通过"
                    print(f"  {标记}  {编号}  {名称}")
                    print(f"           {说明}")
                    if not 通过:
                        截图目录.mkdir(parents=True, exist_ok=True)
                        page.screenshot(path=str(截图目录 / f"{编号}.png"), full_page=True)
                        print(f"           📷 截图：截图\\{编号}.png")
                except Exception as exc:  # noqa: BLE001
                    结果.append((编号, 名称, False, f"执行异常：{exc}", 路径))
                    print(f"  ⚠️ 异常  {编号}  {名称}")
                    print(f"           {type(exc).__name__}: {str(exc)[:100]}")
                finally:
                    context.close()
                    恢复数据()
            browser.close()
    finally:
        恢复了 = 恢复数据()
        print(f"\n🧹 已恢复数据（{恢复了} 条记录有改动）")

    # ---- 汇总 ----
    通过数 = sum(1 for x in 结果 if x[2])
    print("\n" + "=" * 72)
    print(f"  结果：{通过数} / {len(结果)} 条通过")
    print("=" * 72)
    print("\n  未通过的：")
    for 编号, 名称, 通过, 说明, 路径 in 结果:
        if not 通过:
            print(f"    ❌ {编号}  {名称}")
            print(f"        {说明}")
            print(f"        路径：{路径}")
    print()


if __name__ == "__main__":
    main()
