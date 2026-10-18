# -*- coding: utf-8 -*-
"""
搜索功能。

重点覆盖：
- 正常搜索
- 空关键词
- 无结果
- 分页的异常参数（非数字 / 负数）
- 特殊字符（SQL 通配符）
"""

from pages import 搜索页


def test_搜索有结果(页面):
    """搜索 bread 应该能搜到内容"""
    页 = 搜索页(页面)
    响应 = 页.搜索("bread")

    assert 响应.status == 200
    assert 页.结果数() > 0, "搜索 bread 没有返回任何结果"
    assert "You searched for" in 页.摘要文字()


def test_搜索无结果时给出明确提示(页面):
    """搜索一个不存在的词，应显示「No results found」且不报错"""
    页 = 搜索页(页面)
    响应 = 页.搜索("zzzzzzzzzz")

    assert 响应.status == 200
    assert 页.结果数() == 0
    assert 页.显示无结果(), "没有看到「No results found」提示"


def test_空关键词搜索不报错(页面):
    """q 为空时页面应正常渲染"""
    页 = 搜索页(页面)
    响应 = 页.搜索("")

    assert 响应.status == 200
    assert 页.结果数() == 0


def test_页码为非数字时回退到第一页(页面):
    """?page=abc 应被正常处理（代码里有 PageNotAnInteger 分支）"""
    页 = 搜索页(页面)
    响应 = 页.搜索("bread", 页码="abc")

    assert 响应.status == 200, f"页码非数字导致 {响应.status}"
    assert 页.结果数() > 0, "回退后应该能看到第一页结果"


def test_页码为负数时不报服务器错误(页面):
    """
    ?page=-1

    代码里只处理了「非整数」和「超出范围」，没有单独处理负数。
    这一条专门验证这个可疑点。
    """
    页 = 搜索页(页面)
    响应 = 页.搜索("bread", 页码=-1)

    assert 响应.status == 200, f"页码为负数导致 HTTP {响应.status}"


def test_搜索关键词为百分号不报错(页面):
    """
    ?q=%

    % 是 SQL LIKE 的通配符。如果后端没转义，
    可能返回全部数据或直接报错。
    """
    页 = 搜索页(页面)
    响应 = 页.搜索("%")

    assert 响应.status == 200, f"搜索 % 导致 HTTP {响应.status}"
