# -*- coding: utf-8 -*-
"""面包列表页 /breads/"""

from playwright.sync_api import Page

from pages.base_page import BasePage


class 面包列表页(BasePage):
    PATH = "breads/"

    def __init__(self, page: Page):
        super().__init__(page)
        self.卡片 = page.locator(".listing-card")
        self.面包链接 = page.locator('.listing-card__link[href^="/breads/"]')

    def 卡数(self) -> int:
        """列表上一共有多少个面包卡片"""
        return self.卡片.count()

    def 面包链接数(self) -> int:
        return self.面包链接.count()

    def 打开第一个面包(self) -> str:
        """点第一个面包进入详情页，返回进入后的 H1 标题"""
        第一张 = self.卡片.first
        标题 = (第一张.locator("h2, h3").first.inner_text() or "").strip()
        第一张.locator("a").first.click()
        self.page.wait_for_load_state("domcontentloaded")
        return 标题
