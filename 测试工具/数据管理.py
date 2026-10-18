# -*- coding: utf-8 -*-
"""
数据管理 —— 测试数据的「快照 / 恢复」工具

配合 验证助手.py 使用：
    测试前：  python 数据管理.py 保存      ← 把当前数据存下来
    测试中：  手工在后台改数据
    测试后：  python 数据管理.py 恢复      ← 一键恢复原样

注意：这个脚本需要 Django，必须用 bakerydemo 的虚拟环境来跑。
      （验证助手.py 用的是全局 Python，因为只需要 Playwright）

用法：
    python 数据管理.py 保存
    python 数据管理.py 恢复
    python 数据管理.py 查看
"""

import json
import os
import sys
from pathlib import Path

BAKERY = Path(r"C:\AI文件夹\bakerydemo")
快照文件 = Path(__file__).parent / "数据快照.json"

# 自动切换到 bakerydemo 的虚拟环境再运行（那里才有 Django）
VENV_PY = BAKERY / ".venv" / "Scripts" / "python.exe"
if VENV_PY.exists():
    try:
        当前 = Path(sys.executable).resolve()
        if 当前 != VENV_PY.resolve():
            os.execv(str(VENV_PY), [str(VENV_PY), os.path.abspath(__file__)] + sys.argv[1:])
    except Exception:
        pass

if not BAKERY.exists():
    print(f"❌ 找不到 bakerydemo 项目：{BAKERY}")
    sys.exit(1)

# 让 Django 能找到项目
sys.path.insert(0, str(BAKERY))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "bakerydemo.settings.dev")

import django  # noqa: E402

django.setup()

from bakerydemo.blog.models import BlogPage           # noqa: E402
from bakerydemo.breads.models import BreadIngredient, BreadPage  # noqa: E402
from bakerydemo.locations.models import LocationPage  # noqa: E402

# 每个模型要快照的字段
#   注意：body 是富文本（JSONField），序列化需要模板渲染，这里不做快照，
#        如果你改了正文，需要手工恢复。
要保存的字段 = {
    "BreadPage": (BreadPage, ["title", "introduction", "slug",
                              "seo_title", "search_description"]),
    "BlogPage": (BlogPage, ["title", "subtitle", "introduction", "slug",
                            "seo_title", "search_description"]),
    "LocationPage": (LocationPage, ["title", "introduction", "slug",
                                    "seo_title", "search_description", "address"]),
    "BreadIngredient": (BreadIngredient, ["name"]),
}


def 保存():
    """把当前所有关键字段存到 JSON"""
    数据 = {}
    for 名称, (模型, 字段们) in 要保存的字段.items():
        条目 = {}
        for obj in 模型.objects.all():
            # 有些模型没有这些字段，跳过不存在的
            值 = {f: getattr(obj, f, None) for f in 字段们}
            条目[str(obj.pk)] = 值
        数据[名称] = 条目

    快照文件.write_text(json.dumps(数据, ensure_ascii=False, indent=2, default=str),
                        encoding="utf-8")

    总数 = sum(len(v) for v in 数据.values())
    print(f"✅ 已保存快照：{快照文件}")
    print(f"   共 {总数} 条记录：")
    for k, v in 数据.items():
        print(f"     {k}: {len(v)} 条")


def 恢复():
    """从 JSON 把数据改回去"""
    if not 快照文件.exists():
        print(f"❌ 没有找到快照文件：{快照文件}")
        print("   请先运行：python 数据管理.py 保存")
        return 1

    数据 = json.loads(快照文件.read_text(encoding="utf-8"))

    改动数 = 0
    for 名称, (模型, 字段们) in 要保存的字段.items():
        条目 = 数据.get(名称, {})
        for obj in 模型.objects.all():
            原值 = 条目.get(str(obj.pk))
            if not 原值:
                continue
            有改动 = False
            for f in 字段们:
                if f not in 原值:
                    continue
                当前 = getattr(obj, f, None)
                原始 = 原值[f]
                if str(当前) != str(原始):
                    setattr(obj, f, 原始)
                    有改动 = True
            if 有改动:
                obj.save()
                改动数 += 1
                print(f"   已恢复：{名称} #{obj.pk}")

    if 改动数:
        print(f"\n✅ 恢复完成，共改回 {改动数} 条记录")
    else:
        print("\n✅ 数据本身就是原样，无需恢复")
    return 0


def 查看():
    """显示当前的关键字段值"""
    for 名称, (模型, 字段们) in 要保存的字段.items():
        print(f"\n=== {名称}（{模型.objects.count()} 条）===")
        for obj in 模型.objects.all()[:6]:
            展示 = getattr(obj, "title", None) or getattr(obj, "name", None) or obj.pk
            if 名称 == "BreadIngredient":
                print(f"  #{obj.pk} {obj.name}")
            else:
                print(f"  #{obj.pk} 「{展示}」 slug={getattr(obj,'slug','')}")
    return 0


if __name__ == "__main__":
    命令 = sys.argv[1] if len(sys.argv) > 1 else "查看"
    if 命令 == "保存":
        保存()
    elif 命令 == "恢复":
        sys.exit(恢复())
    else:
        查看()
