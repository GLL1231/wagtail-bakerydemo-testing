# -*- coding: utf-8 -*-
"""搜索页 /search/"""

from urllib.parse import urlencode

from playwright.sync_api import Page

from config import url
from pages.base_page import BasePage


class 搜索页(BasePage):
    PATH = "search/"

    def __init__(self, page: Page):
        super().__init__(page)
        self.结果 = page.locator(".search__results li.listing-card")
        self.摘要 = page.locator(".search__introduction")
        self.搜索框 = page.locator("#search-input")

    def 搜索(self, 关键词: str, 页码=None):
        """
        直接构造 URL 发起搜索，返回 HTTP 响应对象。

        关键词和页码都会做 URL 编码，所以 % & 这类特殊字符能安全传入。
        """
        参数 = {"q": 关键词}
        if 页码 is not None:
            参数["page"] = 页码
        return self.page.goto(url("search/") + "?" + urlencode(参数))

    def 结果数(self) -> int:
        return self.结果.count()

    def 有结果(self) -> bool:
        return self.结果数() > 0

    def 摘要文字(self) -> str:
        try:
            return (self.摘要.first.inner_text() or "").strip()
        except Exception:
            return ""

    def 显示无结果(self) -> bool:
        return "No results found" in self.正文
