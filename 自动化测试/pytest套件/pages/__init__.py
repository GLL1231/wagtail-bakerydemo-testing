# -*- coding: utf-8 -*-
"""Page Object 层：每个前台页面一个类。"""

from pages.base_page import BasePage
from pages.breads_page import 面包列表页
from pages.contact_page import 联系表单页
from pages.home_page import 首页
from pages.location_page import 门店页
from pages.search_page import 搜索页

__all__ = ["BasePage", "首页", "面包列表页", "搜索页", "联系表单页", "门店页"]
