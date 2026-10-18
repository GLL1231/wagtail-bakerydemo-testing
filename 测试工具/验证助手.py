# -*- coding: utf-8 -*-
"""
验证助手 —— 手工测试的"半自动"小工具

用法：你在后台手工改完数据，然后用这个脚本检查前台对不对。

------------------------------------------------------------------
常用示例
------------------------------------------------------------------
1) 检查页面里有没有某个文字（最常用）
   python 验证助手.py /breads/bagel/ --包含 "Bagel"

2) 检查页面里【不应该】出现某个文字
   python 验证助手.py /breads/bagel/ --不含 "旧标题"

3) 检查页面大标题（H1）是什么
   python 验证助手.py /breads/bagel/ --标题 "Bagel"

4) 检查页面有没有横向溢出（排版有没有撑破）
   python 验证助手.py /breads/ --无横向溢出

5) 检查 HTTP 状态码
   python 验证助手.py /no-such-page/ --状态 404

6) 截图说明
   默认：只有检查【失败】时才自动截图（作为缺陷证据）
   总是截图：  --截图
   从不截图：  --不截图

7) 多个检查可以一起用
   python 验证助手.py /breads/bagel/ --标题 "Bagel" --包含 "Flour" --无横向溢出

------------------------------------------------------------------
参数说明
------------------------------------------------------------------
--包含 文字      页面可见文字里必须包含它
--不含 文字      页面可见文字里不能包含它
--标题 文字      页面 H1 大标题必须正好等于它
--状态 数字      HTTP 状态码必须等于它
--无横向溢出     页面不能出现横向滚动条
--等 毫秒        打开后先等一会儿再检查（默认 1000）
--截图          保存一张截图到 截图/ 目录
"""

import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8000"
截图目录 = Path(__file__).parent / "截图"
本目录 = Path(__file__).parent

# 恢复数据要用 bakerydemo 的虚拟环境（那里才有 Django）
VENV_PYTHON = r"C:\AI文件夹\bakerydemo\.venv\Scripts\python.exe"
数据管理脚本 = 本目录 / "数据管理.py"
快照文件 = 本目录 / "数据快照.json"


def 拼网址(路径: str) -> str:
    if 路径.startswith("http://") or 路径.startswith("https://"):
        return 路径
    return BASE + "/" + 路径.lstrip("/")


def main():
    parser = argparse.ArgumentParser(
        description="验证助手：检查前台页面的展示是否正确",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("路径", help="要检查的页面路径，如 /breads/bagel/")
    parser.add_argument("--包含", dest="包含", help="页面文字里必须包含")
    parser.add_argument("--不含", dest="不含", help="页面文字里不能包含")
    parser.add_argument("--标题", dest="标题", help="H1 大标题必须等于")
    parser.add_argument("--状态", dest="状态", type=int, help="HTTP 状态码必须等于")
    parser.add_argument("--无横向溢出", dest="无横向溢出", action="store_true",
                        help="页面不能出现横向滚动条")
    parser.add_argument("--元素数", dest="元素数", nargs=2,
                        metavar=("选择器", "数量"),
                        help='页面上该选择器匹配的数量必须等于 N，'
                             '如 --元素数 ".listing-card" 11')
    parser.add_argument("--等", dest="等待", type=int, default=1000,
                        help="打开后等待毫秒数（默认 1000）")
    parser.add_argument("--截图", dest="截图", action="store_true",
                        help="总是保存截图（默认只在检查失败时保存）")
    parser.add_argument("--不截图", dest="不截图", action="store_true",
                        help="任何情况下都不保存截图")
    parser.add_argument("--不恢复", dest="不恢复", action="store_true",
                        help="不自动恢复数据（默认在检查全部通过后会自动恢复）")
    parser.add_argument("--恢复", dest="恢复", action="store_true",
                        help="（兼容旧写法；现在默认就会恢复，此参数可省略）")

    args = parser.parse_args()
    网址 = 拼网址(args.路径)

    print()
    print("=" * 62)
    print(f"  检查页面：{网址}")
    print("=" * 62)

    结果 = []          # (名称, 是否通过, 说明)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        page.set_default_timeout(20000)

        try:
            response = page.goto(网址, wait_until="domcontentloaded")
            page.wait_for_timeout(args.等待)

            状态码 = response.status if response else None
            正文 = page.locator("body").inner_text()
            主标题 = (page.locator("h1").first.inner_text() or "").strip()

            # ---- 逐项检查 ----
            if args.状态 is not None:
                通过 = (状态码 == args.状态)
                结果.append(("HTTP 状态码", 通过, f"期望 {args.状态}，实际 {状态码}"))

            if args.标题 is not None:
                通过 = (主标题 == args.标题)
                结果.append(("H1 大标题", 通过, f"期望「{args.标题}」，实际「{主标题}」"))

            if args.包含 is not None:
                通过 = (args.包含 in 正文)
                结果.append((f"包含「{args.包含}」", 通过,
                             "已找到" if 通过 else "页面里没有找到这段文字"))

            if args.不含 is not None:
                通过 = (args.不含 not in 正文)
                结果.append((f"不含「{args.不含}」", 通过,
                             "确认没有" if 通过 else "竟然出现了这段文字"))

            if args.无横向溢出:
                溢出 = page.evaluate(
                    "() => document.documentElement.scrollWidth > "
                    "document.documentElement.clientWidth"
                )
                结果.append(("无横向溢出", not 溢出,
                             "排版正常" if not 溢出 else "出现横向滚动条，排版被撑破"))

            if args.元素数:
                选择器, 期望数 = args.元素数
                try:
                    实际数 = page.locator(选择器).count()
                except Exception as exc:  # noqa: BLE001
                    结果.append((f"元素数 {选择器}", False, f"选择器出错：{exc}"))
                else:
                    通过 = (实际数 == int(期望数))
                    结果.append((f"元素数 {选择器} = {期望数}", 通过,
                                 f"实际匹配到 {实际数} 个"))

            # ---- 截图：默认只在检查失败时截（作为缺陷证据）----
            if args.不截图:
                需要截图 = False
            elif args.截图:
                需要截图 = True                                  # 强制总是截图
            else:
                需要截图 = any(not ok for _, ok, _ in 结果)       # 有失败才截

            if 需要截图:
                try:
                    截图目录.mkdir(parents=True, exist_ok=True)
                    名 = datetime.now().strftime("%H%M%S") + "_" + \
                         (args.路径.strip("/").replace("/", "_") or "home")
                    # 去掉 Windows 文件名里不允许的字符（< > : " / \ | ? *）
                    import re as _re
                    名 = _re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", 名)
                    路径 = 截图目录 / f"{名}.png"
                    page.screenshot(path=str(路径), full_page=True)
                    print(f"\n  📷 截图已保存：{路径}")
                except Exception as exc:  # noqa: BLE001
                    print(f"\n  ⚠️ 截图保存失败（不影响检查结果）：{exc}")

        finally:
            context.close()
            browser.close()

    # ---- 输出 ----
    print()
    if not 结果:
        print("  （没有指定任何检查项，只打开了页面）")
    else:
        通过数 = 0
        for 名称, 通过, 说明 in 结果:
            标记 = "✅ 通过" if 通过 else "❌ 不通过"
            if 通过:
                通过数 += 1
            print(f"  {标记}  {名称}")
            print(f"           {说明}")
        print()
        print("-" * 62)
        print(f"  结果：{通过数} / {len(结果)} 项通过")
        print("-" * 62)

    全通过 = all(x[1] for x in 结果)

    # ---- 自动恢复数据（默认开启；加 --不恢复 可关闭）----
    if not args.不恢复:
        print()
        if not 结果:
            print("  ⚠️ 没有检查项，不执行恢复")
        elif not 全通过:
            print("  ⚠️ 有检查未通过，【保留现场不恢复】—— 方便你排查问题")
            print("     排查完想恢复，手动运行：python 数据管理.py 恢复")
        elif not 快照文件.exists():
            print("  ⚠️ 找不到数据快照，无法恢复")
            print("     请在开始测试前先运行：python 数据管理.py 保存")
        elif not Path(VENV_PYTHON).exists():
            print(f"  ⚠️ 找不到 bakerydemo 的虚拟环境：{VENV_PYTHON}")
        else:
            print("  🔄 检查全部通过，正在恢复数据……")
            try:
                r = subprocess.run(
                    [VENV_PYTHON, str(数据管理脚本), "恢复"],
                    capture_output=True, text=True, encoding="utf-8",
                    errors="replace", timeout=120,
                )
                输出 = (r.stdout or "").strip() or (r.stderr or "").strip()
                for line in 输出.splitlines():
                    print("     " + line)
            except Exception as exc:  # noqa: BLE001
                print(f"  ❌ 恢复失败：{exc}")

    return 0 if 全通过 else 1


if __name__ == "__main__":
    sys.exit(main())
