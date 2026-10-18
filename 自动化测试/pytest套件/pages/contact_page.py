# -*- coding: utf-8 -*-
"""联系表单页 /contact-us/"""

from playwright.sync_api import Page

from pages.base_page import BasePage


class 联系表单页(BasePage):
    PATH = "contact-us/"

    def __init__(self, page: Page):
        super().__init__(page)
        self.主题框 = page.locator("#id_subject")
        self.姓名框 = page.locator("#id_your_name")
        self.邮箱框 = page.locator("#id_your_email")
        self.目的框 = page.locator("#id_purpose")
        self.正文框 = page.locator("#id_body")
        self.提交按钮 = page.locator('form[action="/contact-us/"] input[type="submit"]')
        self.成功提示 = page.locator(".form-page-thanks")

    def 选择第一个目的(self):
        """purpose 是下拉框，选第一个有值的选项"""
        for opt in self.目的框.locator("option").all():
            v = opt.get_attribute("value")
            if v:
                self.目的框.select_option(value=v)
                return v
        return None

    def 填写(self, 主题="", 姓名="", 邮箱="", 正文=""):
        if 主题:
            self.主题框.fill(主题)
        if 姓名:
            self.姓名框.fill(姓名)
        if 邮箱:
            self.邮箱框.fill(邮箱)
        if 正文:
            self.正文框.fill(正文)
        self.选择第一个目的()
        return self

    def 提交(self):
        self.提交按钮.click()
        self.page.wait_for_load_state("domcontentloaded")
        return self

    def 提交成功(self) -> bool:
        return "We've received your message" in self.正文
