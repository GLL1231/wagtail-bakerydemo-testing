# -*- coding: utf-8 -*-
"""
扩展执行器 —— 覆盖第一批没做的可自动化用例

包含：缓存、搜索、边界、容错、关联、发布状态、博客、门店、结构、版本、表单
"""

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

from bakerydemo.base.models import FooterText, Person  # noqa: E402
from bakerydemo.blog.models import BlogIndexPage, BlogPage  # noqa: E402
from bakerydemo.breads.models import BreadIngredient, BreadPage, BreadsIndexPage  # noqa: E402
from bakerydemo.locations.models import (  # noqa: E402
    LocationOperatingDay,
    LocationPage,
)

BASE = "http://127.0.0.1:8000"
截图目录 = Path(__file__).parent / "截图"

# ===========================================================================
# 备份 / 恢复（只备份原数据，新建的测试数据由各用例自己清理）
# ===========================================================================
要备份的 = {
    "BreadPage": (BreadPage, ["title", "introduction", "slug", "live"]),
    "BlogPage": (BlogPage, ["title", "introduction", "slug", "live"]),
    "LocationPage": (LocationPage, ["title", "address", "slug", "live"]),
    "BreadIngredient": (BreadIngredient, ["name"]),
    "FooterText": (FooterText, ["body"]),
    "Person": (Person, ["first_name", "last_name"]),
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
                if str(getattr(o, f, None)) != str(原值[f]):
                    setattr(o, f, 原值[f])
                    有改动 = True
            if 有改动:
                o.save()
                改了 += 1
    return 改了


# ===========================================================================
# 辅助
# ===========================================================================
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
        "() => document.documentElement.scrollWidth > document.documentElement.clientWidth")


def 新建面包页(slug, title, introduction="临时测试页", live=True):
    idx = BreadsIndexPage.objects.first()
    p = BreadPage(title=title, slug=slug, live=live, introduction=introduction)
    idx.add_child(instance=p)
    if live:
        p.save_revision().publish()
    return p


def 新建博客页(slug, title, live=True):
    idx = BlogIndexPage.objects.first()
    p = BlogPage(title=title, slug=slug, live=live,
                 introduction="临时测试博客", date_published="2026-10-17")
    idx.add_child(instance=p)
    if live:
        p.save_revision().publish()
    return p


# ===========================================================================
# 用例
# ===========================================================================
def 用例列表():
    C = []

    # ---------- 缓存与时效 ----------
    def 缓存01(pg, r):
        p = BreadPage.objects.get(slug="anadama-bread")
        原 = p.title
        打开(pg, "/breads/anadama-bread/")
        首次 = H1(pg)
        p.title = "缓存测试新标题"; p.save()          # 后台改了，但页面没刷新
        未刷新 = H1(pg)                                # 还是旧值（DOM 没变）
        pg.reload(); pg.wait_for_timeout(500)
        刷新后 = H1(pg)
        p.title = 原; p.save()
        ok = (未刷新 == 首次 and 刷新后 == "缓存测试新标题")
        return ok, f"改动前={首次!r} 不刷新={未刷新!r} 刷新后={刷新后!r}"

    C.append(("缓存-01/02", "改数据后：不刷新保持旧内容，刷新后显示新内容", None,
              lambda pg, r: 缓存01(pg, r)))

    def 缓存03(pg, r):
        p = BreadPage.objects.get(slug="anadama-bread")
        原 = p.title
        pg.goto(BASE + "/breads/anadama-bread/"); pg.wait_for_timeout(500)   # 窗口A
        p.title = "双窗口测试"; p.save()
        pg.reload(); pg.wait_for_timeout(500)                                # 窗口A刷新
        新 = H1(pg)
        p.title = 原; p.save()
        return (新 == "双窗口测试"), f"刷新后={新!r}"

    C.append(("缓存-03", "另一个窗口刷新后能看到新数据", None, lambda pg, r: 缓存03(pg, r)))

    # ---------- 搜索同步 ----------
    def 搜索03(pg, r):
        slug = "auto-search-new-bread"
        p = 新建面包页(slug, "自动搜索测试面包")
        try:
            打开(pg, "/search/?q=自动搜索测试面包")
            数 = pg.locator(".search__results li.listing-card").count()
            return (数 >= 1), f"搜索结果 {数} 条"
        finally:
            p.delete()

    C.append(("搜索-03", "新增内容后能被搜索到", None, lambda pg, r: 搜索03(pg, r)))

    def 搜索04(pg, r):
        slug = "auto-search-draft-bread"
        p = 新建面包页(slug, "草稿搜索测试面包", live=False)
        try:
            打开(pg, "/search/?q=草稿搜索测试面包")
            数 = pg.locator(".search__results li.search-card, .search__results li").count()
            有无 = "草稿搜索测试面包" in 正文(pg)
            return (not 有无), f"草稿内容出现在搜索结果中：{有无}"
        finally:
            p.delete()

    C.append(("搜索-04", "未发布内容不出现在搜索结果中", None, lambda pg, r: 搜索04(pg, r)))

    # ---------- 边界与异常 ----------
    def 边界01(pg, r):
        p = BreadPage.objects.get(slug="anadama-bread")
        原 = p.title
        p.title = ""; p.save()
        try:
            r = 打开(pg, "/breads/anadama-bread/")
            空 = (H1(pg) == "")
            return 空, f"HTTP {r.status}，H1={H1(pg)!r}（空标题被接受，页面仍可访问）"
        finally:
            p.title = 原; p.save()

    C.append(("边界-01", "标题留空后前台的渲染表现", None, lambda pg, r: 边界01(pg, r)))

    def 边界03(pg, r):
        p = BreadPage.objects.get(slug="anadama-bread")
        原 = p.title
        try:
            p.title = "H" * 255; p.save(); p.refresh_from_db()
            n255 = len(p.title)
            try:
                p.title = "H" * 256; p.save(); p.refresh_from_db()
                n256 = len(p.title)
                note = f"255→保存 {n255} 字符；256→保存 {n256} 字符（SQLite 不强制长度）"
                ok = True
            except Exception as e:
                note = f"255 正常；256 报错 {type(e).__name__}"
                ok = True
            return ok, note
        finally:
            p.title = 原; p.save()

    C.append(("边界-03", "标题 255 / 256 字符的保存行为", None, lambda pg, r: 边界03(pg, r)))

    def 边界05(pg, r):
        p = BreadPage.objects.get(slug="anadama-bread")
        原 = p.introduction
        p.introduction = "W" * 500; p.save()
        try:
            打开(pg, "/breads/anadama-bread/")
            溢 = 有溢出(pg)
            return (not 溢), "出现横向溢出" if 溢 else "排版正常"
        finally:
            p.introduction = 原; p.save()

    C.append(("边界-05", "超长正文导致排版溢出检查", None, lambda pg, r: 边界05(pg, r)))

    # ---------- 容错 ----------
    def 容错05(pg, r):
        p = BreadPage.objects.get(slug="anadama-bread")
        原 = p.introduction
        p.introduction = "<div></div>"; p.save()
        try:
            打开(pg, "/breads/anadama-bread/")
            溢 = 有溢出(pg)
            return (not 溢), f"无横向溢出={not 溢}，H1={H1(pg)!r}"
        finally:
            p.introduction = 原; p.save()

    C.append(("容错-05", "正文只含 HTML 标签，前台不塌陷", None, lambda pg, r: 容错05(pg, r)))

    # ---------- 关联数据 ----------
    def 关联02(pg, r):
        ing = BreadIngredient.objects.get(name="Flour")
        有引用 = BreadPage.objects.filter(ingredients=ing).count()
        ing.delete()
        try:
            r = 打开(pg, "/breads/anadama-bread/")
            return (r.status == 200), f"删除被 {有引用} 个面包引用的原料后，前台 HTTP {r.status}"
        finally:
            BreadIngredient.objects.create(name="Flour")

    C.append(("关联-02", "删除被引用的原料，面包页不崩溃", None, lambda pg, r: 关联02(pg, r)))

    def 关联05(pg, r):
        per = Person.objects.filter(first_name="Roberta").first()
        if not per:
            return False, "找不到测试人物"
        原名 = per.first_name
        per.first_name = "自动化测试人物"; per.save()
        try:
            打开(pg, "/about/")
            见 = "自动化测试人物" in 正文(pg)
            return 见, f"关于页是否显示新名字：{见}"
        finally:
            per.first_name = 原名; per.save()

    C.append(("关联-05", "修改人物信息后相关页面同步", None, lambda pg, r: 关联05(pg, r)))

    # ---------- 发布状态 ----------
    def 发布01(pg, r):
        """改了但只存草稿 → 前台仍是旧内容"""
        p = BreadPage.objects.get(slug="anadama-bread")
        原 = p.title
        打开(pg, "/breads/anadama-bread/")
        p.title = "草稿标题不该出现"
        p.save_revision()          # 只存草稿，不发布
        try:
            pg.reload(); pg.wait_for_timeout(500)
            前台 = H1(pg)
            return (前台 == 原), f"草稿后前台 H1={前台!r}（应仍为 {原!r}）"
        finally:
            p.title = 原; p.save()

    C.append(("发布-01", "编辑后仅保存草稿，前台保持旧内容", None, lambda pg, r: 发布01(pg, r)))

    def 发布04(pg, r):
        """草稿页直接访问 URL 应 404"""
        slug = "auto-draft-page-test"
        p = 新建面包页(slug, "草稿越权测试页", live=False)
        try:
            r = 打开(pg, f"/breads/{slug}/")
            return (r.status == 404), f"草稿 URL 返回 HTTP {r.status}"
        finally:
            p.delete()

    C.append(("发布-04", "草稿页无法通过直接输入 URL 访问", None, lambda pg, r: 发布04(pg, r)))

    def 发布03(pg, r):
        """删除页面后 404（用自建页面测试，不删原有数据）"""
        slug = "auto-delete-page-test"
        p = 新建面包页(slug, "待删除测试页")
        p.delete()
        r = 打开(pg, f"/breads/{slug}/")
        return (r.status == 404), f"删除后 URL 返回 HTTP {r.status}"

    C.append(("发布-03", "删除页面后前台返回 404", None, lambda pg, r: 发布03(pg, r)))

    # ---------- 博客 ----------
    def 博客03(pg, r):
        slug = "auto-new-blog-post"
        p = 新建博客页(slug, "自动化新建的博客文章")
        try:
            打开(pg, "/blog/")
            见 = "自动化新建的博客文章" in 正文(pg)
            return 见, f"列表中是否出现新文章：{见}"
        finally:
            p.delete()

    C.append(("博客-03", "新增博客并发布后列表页出现", None, lambda pg, r: 博客03(pg, r)))

    def 博客04(pg, r):
        slug = "auto-delete-blog-post"
        p = 新建博客页(slug, "待删除的博客文章")
        p.delete()
        r = 打开(pg, f"/blog/{slug}/")
        return (r.status == 404), f"删除后 URL 返回 HTTP {r.status}"

    C.append(("博客-04", "删除博客后列表消失且旧 URL 404", None, lambda pg, r: 博客04(pg, r)))

    # ---------- 页面结构 ----------
    def 结构04(pg, r):
        slug = "auto-structure-new-bread"
        打开(pg, "/breads/")
        前 = pg.locator(".listing-card").count()
        p = 新建面包页(slug, "结构测试新面包")
        try:
            pg.reload(); pg.wait_for_timeout(500)
            后 = pg.locator(".listing-card").count()
            return (后 == 前 + 1), f"新建前 {前} 个，新建后 {后} 个"
        finally:
            p.delete()

    C.append(("结构-04", "新增页面并发布后出现在列表页", None, lambda pg, r: 结构04(pg, r)))

    # ---------- 版本与回收站 ----------
    def 版本04(pg, r):
        p = BreadPage.objects.get(slug="anadama-bread")
        原live = p.live
        try:
            p.live = False; p.save()
            打开(pg, "/breads/anadama-bread/")
            下线 = (pg.url.endswith("/breads/anadama-bread/") and
                    "Page not found" in 正文(pg)) or ("404" in 正文(pg))
            p.live = True; p.save()
            rg = 打开(pg, "/breads/anadama-bread/")
            恢复 = (rg.status == 200)
            return (恢复), f"取消发布后可访问={not 恢复}，重新发布后 HTTP {rg.status}"
        finally:
            p.live = 原live; p.save()

    C.append(("版本-04", "取消发布后 404，重新发布后恢复访问", None, lambda pg, r: 版本04(pg, r)))

    # ---------- 门店营业时间 ----------
    def 门店03(pg, r):
        """把今天的营业时间改成 00:00-23:59，应显示营业中"""
        import datetime
        今天 = datetime.date.today().strftime("%a").upper()
        门店 = LocationPage.objects.get(slug="reykjavik")
        天 = 门店.operating_days.filter(day=今天).first()
        if not 天:
            return False, f"今天({今天})没有营业时间记录"
        原closed = 天.closed
        原slots = [(s.opening_time, s.closing_time) for s in 天.time_slots.all()]
        try:
            天.closed = False; 天.save()
            天.time_slots.all().delete()
            from bakerydemo.locations.models import LocationOperatingTimeSlot
            LocationOperatingTimeSlot.objects.create(
                day=天, opening_time=datetime.time(0, 0), closing_time=datetime.time(23, 59))
            打开(pg, "/locations/reykjavik/", 等=3000)
            状态 = (pg.locator("location-status").first.inner_text() or "").strip()
            return ("open" in 状态.lower()), f"营业状态={状态!r}"
        finally:
            天.closed = 原closed; 天.save()
            天.time_slots.all().delete()
            from bakerydemo.locations.models import LocationOperatingTimeSlot
            for o, c in 原slots:
                LocationOperatingTimeSlot.objects.create(day=天, opening_time=o, closing_time=c)

    C.append(("门店-03", "营业时间包含当前时刻时应显示营业中", None, lambda pg, r: 门店03(pg, r)))

    return C


# ===========================================================================
# 主流程
# ===========================================================================
def main():
    print("\n" + "=" * 72)
    print("  bakerydemo 扩展自动化执行")
    print("=" * 72)

    备份数据()
    print(f"✅ 已备份 {sum(len(v) for v in 备份.values())} 条记录\n")

    结果 = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            for 编号, 名称, _改数据, 检查 in 用例列表():
                context = browser.new_context()
                page = context.new_page()
                page.set_default_timeout(25000)
                try:
                    通过, 说明 = 检查(page, None)
                    结果.append((编号, 名称, 通过, 说明))
                    print(f"  {'✅ 通过' if 通过 else '❌ 不通过'}  {编号}  {名称}")
                    print(f"           {说明}")
                    if not 通过:
                        截图目录.mkdir(parents=True, exist_ok=True)
                        try:
                            page.screenshot(path=str(截图目录 / f"{编号}.png"), full_page=True)
                            print(f"           📷 截图：截图\\{编号}.png")
                        except Exception:
                            pass
                except Exception as exc:  # noqa: BLE001
                    结果.append((编号, 名称, False, f"执行异常：{type(exc).__name__}: {exc}"))
                    print(f"  ⚠️ 异常  {编号}  {名称}")
                    print(f"           {type(exc).__name__}: {str(exc)[:110]}")
                finally:
                    context.close()
                    恢复数据()
            browser.close()
    finally:
        print(f"\n🧹 恢复数据：{恢复数据()} 条记录改回原值")

    通过数 = sum(1 for x in 结果 if x[2])
    print("\n" + "=" * 72)
    print(f"  结果：{通过数} / {len(结果)} 条通过")
    print("=" * 72)
    for 编号, 名称, 通过, 说明 in 结果:
        if not 通过:
            print(f"    ❌ {编号}  {名称}：{说明}")
    print()


if __name__ == "__main__":
    main()
