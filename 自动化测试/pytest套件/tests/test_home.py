# -*- coding: utf-8 -*-
"""首页与全局导航"""

from config import url
from pages import 首页


def test_首页能正常打开(页面):
    """首页返回 200，主标题正确"""
    页 = 首页(页面)
    响应 = 页面.goto(url())
    assert 响应.status == 200, f"首页返回 {响应.status}"
    assert "Welcome to the Wagtail Bakery" in 页.主标题, f"实际标题：{页.主标题}"


def test_导航菜单包含主要板块(页面):
    """顶部导航包含 面包 / 门店 / 博客 / 联系 等入口"""
    导航 = 首页(页面).open().导航项()

    必填项 = ["Breads", "Locations", "Blog", "Contact Us"]
    缺失 = [x for x in 必填项 if x not in 导航]

    assert not 缺失, f"导航中缺少 {缺失}；实际导航：{导航}"


def test_访问不存在的页面返回404(页面):
    """地址栏输入不存在的路径，应返回 404 且页面有提示"""
    响应 = 页面.goto(url("this-page-does-not-exist-xyz/"))

    assert 响应.status == 404, f"期望 404，实际 {响应.status}"
    assert "Page not found" in 页面.locator("h1").first.inner_text()
