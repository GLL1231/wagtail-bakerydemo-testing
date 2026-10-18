# -*- coding: utf-8 -*-
"""所有页面的父类：公共的打开、取标题、溢出检测等。"""

from playwright.sync_api import Page

from config import url


class BasePage:
    PATH = ""

    def __init__(self, page: Page):
        self.page = page

    # ---------------- 基础操作 ----------------
    def open(self):
        """打开这个页面"""
        self.page.goto(url(self.PATH))
        return self

    # ---------------- 读取 ----------------
    @property
    def 主标题(self) -> str:
        """页面上的 H1 大标题"""
        return (self.page.locator("h1").first.inner_text() or "").strip()

    @property
    def 标签页标题(self) -> str:
        """浏览器标签上显示的标题"""
        return self.page.title()

    @property
    def 正文(self) -> str:
        """整页可见文字（用于包含判断）"""
        return self.page.locator("body").inner_text()

    # ---------------- 检查 ----------------
    def 有横向溢出(self) -> bool:
        """
        页面是否出现横向滚动条。

        把「排版有没有撑破」这种主观判断，变成可断言的客观指标。
        """
        return self.page.evaluate(
            "() => document.documentElement.scrollWidth > "
            "document.documentElement.clientWidth"
        )
