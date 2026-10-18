# -*- coding: utf-8 -*-
"""首页 /"""

from playwright.sync_api import Page

from pages.base_page import BasePage


class 首页(BasePage):
    PATH = ""

    def __init__(self, page: Page):
        super().__init__(page)
        self.导航链接 = page.locator("nav a")

    def 导航项(self) -> list:
        """返回顶部导航里所有链接的文字（去空、去重、保序）"""
        结果 = []
        for a in self.导航链接.all():
            try:
                t = (a.inner_text() or "").strip()
                href = a.get_attribute("href") or ""
            except Exception:
                continue
            if t and href.startswith("/") and t not in 结果:
                结果.append(t)
        return 结果
