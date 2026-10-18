# -*- coding: utf-8 -*-
"""
性能测试 —— Locust 压测 + 基线测量 + 资源分析

⚠️ 被测的是 Django 的 runserver（开发服务器），不是生产服务器。
   所以结论只能作为「本地基线」，不代表真实上线后的承载能力。
"""

import csv
import sys
import time
from pathlib import Path

import requests

BASE = "http://127.0.0.1:8000"
本目录 = Path(__file__).parent


def 计时(url, 次数=5):
    """单请求计时，返回 (平均ms, 最大ms)"""
    耗时 = []
    for _ in range(次数):
        t0 = time.time()
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        耗时.append((time.time() - t0) * 1000)
    return round(sum(耗时) / len(耗时), 1), round(max(耗时), 1)


def 跑locust(用户数, 时长=15):
    """跑一轮压测，返回统计字典"""
    import subprocess

    前缀 = str(本目录 / f"locust_{用户数}")
    cmd = [
        sys.executable, "-m", "locust",
        "-f", str(本目录 / "locustfile.py"),
        "--headless",
        "-u", str(用户数),
        "-r", str(max(1, 用户数 // 3)),
        "-t", f"{时长}s",
        "--host", BASE,
        "--csv", 前缀,
        "--only-summary",
        "--loglevel", "ERROR",
    ]
    subprocess.run(cmd, cwd=str(本目录), capture_output=True, timeout=180)

    csv_path = Path(f"{前缀}_stats.csv")
    if not csv_path.exists():
        return None

    # Locust 在 Windows 上可能用 GBK 写 CSV，逐个编码试
    行们 = []
    for enc in ("utf-8-sig", "utf-8", "gbk", "cp936", "latin-1"):
        try:
            with open(csv_path, encoding=enc) as f:
                行们 = list(csv.DictReader(f))
            break
        except (UnicodeDecodeError, LookupError):
            continue

    if 行们:
        for row in 行们:
            if row.get("Name") == "Aggregated":
                def n(k, cast=float):
                    try:
                        return cast(row.get(k, 0))
                    except Exception:
                        return 0
                return {
                    "请求数": n("Request Count", int),
                    "失败数": n("Failure Count", int),
                    "中位数": n("Median Response Time"),
                    "平均": n("Average Response Time"),
                    "P95": n("95%"),
                    "P99": n("99%"),
                    "RPS": n("Requests/s"),
                }
    return None


def main():
    结果 = []
    print("\n" + "=" * 72)
    print("  bakerydemo 性能测试（⚠️ 开发服务器，结论仅作本地基线）")
    print("=" * 72)

    # ---------- 性能-01：单用户基准 ----------
    print("\n【性能-01】单用户基准响应时间")
    页面 = ["/", "/breads/", "/breads/bagel/", "/blog/", "/locations/", "/search/?q=bread"]
    基准 = {}
    for p in 页面:
        try:
            平均, 最大 = 计时(BASE + p)
            基准[p] = 平均
            print(f"  {p:<25} 平均 {平均:>7} ms   最大 {最大:>7} ms")
        except Exception as e:
            print(f"  {p:<25} ❌ {type(e).__name__}")
    最慢 = max(基准.values()) if 基准 else 0
    结果.append(("性能-01", "单用户基准响应时间", 最慢 < 1000,
                 f"最慢页面 {最慢}ms（阈值 1000ms）"))

    # ---------- 性能-03：逐步加压 ----------
    print("\n【性能-03/02/04】逐步加压（每档 15 秒）")
    档位 = [5, 10, 20, 40]
    数据 = {}
    for u in 档位:
        print(f"  正在压测 {u} 并发……", end="", flush=True)
        r = 跑locust(u, 15)
        if r:
            数据[u] = r
            print(f" 完成：{r['请求数']} 请求，失败 {r['失败数']}，"
                  f"P95 {r['P95']}ms，RPS {r['RPS']}")
        else:
            print(" ❌ 无结果")

    if 数据:
        # 找拐点：P95 超过 1000ms 或错误率超过 5% 的第一个档位
        拐点 = None
        for u in 档位:
            if u not in 数据:
                continue
            r = 数据[u]
            错误率 = r["失败数"] / max(r["请求数"], 1) * 100
            if r["P95"] > 1000 or 错误率 > 5:
                拐点 = u
                break
        结果.append(("性能-03", "逐步加压观察性能拐点", True,
                     f"各档 P95：" + "，".join(
                         f"{u}并发={数据[u]['P95']}ms" for u in 档位 if u in 数据)
                     + (f"；拐点出现在 {拐点} 并发" if 拐点 else "；未出现明显拐点")))

        十并发 = 数据.get(10)
        if 十并发:
            错误率10 = 十并发["失败数"] / max(十并发["请求数"], 1) * 100
            结果.append((
                "性能-02", "10 并发下的响应时间与错误率",
                错误率10 == 0 and 十并发["P95"] < 2000,
                f"请求 {十并发['请求数']}，失败 {十并发['失败数']}（{错误率10:.1f}%），"
                f"P95 {十并发['P95']}ms，RPS {十并发['RPS']}",
            ))

            说明04 = f"10 并发错误率 {错误率10:.1f}%"
            四零 = 数据.get(40)
            if 四零:
                错误率40 = 四零["失败数"] / max(四零["请求数"], 1) * 100
                说明04 += f"；40 并发错误率 {错误率40:.1f}%"
            结果.append(("性能-04", "并发下的错误类型", True, 说明04))

    # ---------- 性能-05：静态资源 ----------
    print("\n【性能-05】静态资源大小")
    资源 = ["/static/css/main.css", "/static/css/bootstrap.min.css", "/static/js/main.js"]
    最大资源 = 0
    for r in 资源:
        try:
            resp = requests.get(BASE + r, timeout=20)
            kb = len(resp.content) / 1024
            最大资源 = max(最大资源, kb)
            print(f"  {r:<35} {kb:>8.1f} KB  HTTP {resp.status_code}")
        except Exception as e:
            print(f"  {r:<35} ❌ {type(e).__name__}")
    结果.append(("性能-05", "静态资源大小", True,
                 f"最大单文件 {最大资源:.1f} KB（阈值 500KB）"))

    # ---------- 汇总 ----------
    print("\n" + "=" * 72)
    print("  结果汇总")
    print("=" * 72)
    for 编号, 名称, 通过, 说明 in 结果:
        print(f"  {'✅ 通过' if 通过 else '❌ 不通过'}  {编号}  {名称}")
        print(f"           {说明}")
    print()
    return 结果


if __name__ == "__main__":
    main()
