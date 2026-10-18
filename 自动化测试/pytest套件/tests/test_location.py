# -*- coding: utf-8 -*-
"""门店营业状态（关联已知缺陷 BUG-001）"""

import pytest

from pages import 门店页


@pytest.mark.xfail(
    reason="BUG-001 未修复：/api/v3-preview/ 返回 500，前台无法获取营业状态",
    strict=True,
)
def test_门店营业状态能正常显示(页面):
    """
    打开门店详情页，Operating Status 区域应显示「营业中」或「已关门」。

    实际现象：接口 500，前端显示
    「Sorry, we couldn't retrieve the status of this location.」
    """
    页 = 门店页(页面).打开门店("reykjavik")
    状态 = 页.营业状态文字()

    assert "Please wait" not in 状态, "一直停留在「Please wait…」，组件没有更新"
    assert "couldn't retrieve" not in 状态, (
        f"前台无法获取营业状态（BUG-001 复现）；实际文字：{状态}"
    )
    assert ("open" in 状态.lower()) or ("closed" in 状态.lower()), (
        f"营业状态文字不符合预期：{状态}"
    )
