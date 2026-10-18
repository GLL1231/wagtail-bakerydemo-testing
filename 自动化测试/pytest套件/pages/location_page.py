# -*- coding: utf-8 -*-
"""门店详情页 /locations/<slug>/"""

from playwright.sync_api import Page

from config import url
from pages.base_page import BasePage


class 门店页(BasePage):
    PATH = "locations/"

    def __init__(self, page: Page):
        super().__init__(page)
        self.营业状态组件 = page.locator("location-status")

    def 打开门店(self, slug: str):
        self.page.goto(url(f"locations/{slug}/"))
        return self

    def 营业状态文字(self, 等待毫秒: int = 3000) -> str:
        """
        读取营业状态区域的文字。

        这个组件是通过 fetch 异步请求 API 后才填文字的，
        所以要先等一会儿，不能刚打开就读。
        """
        self.page.wait_for_timeout(等待毫秒)
        try:
            return (self.营业状态组件.first.inner_text() or "").strip()
        except Exception:
            return ""
