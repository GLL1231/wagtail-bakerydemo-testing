# -*- coding: utf-8 -*-
"""界面与响应式"""

from pages import BasePage, 首页


def test_手机尺寸下无横向滚动(页面):
    """手机视口（375×667）下，首页不应出现横向滚动条"""
    页面.set_viewport_size({"width": 375, "height": 667})

    页 = 首页(页面).open()
    assert not 页.有横向溢出(), "手机尺寸下首页出现横向滚动条"


def test_手机尺寸下面包列表无横向滚动(页面):
    """手机视口下面包列表也不应横向溢出"""
    from pages import 面包列表页

    页面.set_viewport_size({"width": 375, "height": 667})

    页 = 面包列表页(页面).open()
    assert not 页.有横向溢出(), "手机尺寸下面包列表出现横向滚动条"


def test_桌面尺寸下无横向滚动(页面):
    """正常桌面尺寸（1280×800）下首页排版正常"""
    页面.set_viewport_size({"width": 1280, "height": 800})

    页 = 首页(页面).open()
    assert not 页.有横向溢出(), "桌面尺寸下首页出现横向滚动条"
