# 自动化测试说明

本目录包含四套自动化，**前提：被测网站已在本机 8000 端口运行**。

```bash
cd bakerydemo
.venv\Scripts\Activate.ps1
python manage.py runserver
```

---

## 一、pytest套件 —— 前台 UI 自动化（19 条）

**需要**：Python + Playwright（全局环境即可，不需要 Django）

```bash
cd pytest套件
pip install -r requirements.txt
playwright install chromium
python -m pytest                 # 无头模式，生成 reports/report.html
python -m pytest --headed        # 打开浏览器窗口观看
python -m pytest tests/test_search.py -v    # 只跑某个模块
```

**结构**：

```
pytest套件/
├── config.py                 被测地址配置
├── conftest.py               夹具：浏览器、页面、失败自动截图、网站连通性预检查
├── pages/                    Page Object（6 个页面类）
└── tests/                    19 条用例
    ├── test_home.py          首页 / 导航 / 404
    ├── test_breads.py        面包列表与详情
    ├── test_search.py        搜索（正常 / 无结果 / 空 / 分页异常 / 特殊字符）
    ├── test_contact.py       表单（提交 / 必填 / 邮箱格式）
    ├── test_location.py      门店营业状态（xfail，对应 BUG-001）
    └── test_ui.py            响应式视口
```

**预期结果**：`18 passed, 1 xfailed`

> 那 1 条 `xfailed` 是 BUG-001 的回归哨兵。缺陷修复后会转为 `XPASS` 并因 `strict=True` 报错，
> 提醒更新缺陷报告。

---

## 二、数据驱动执行器（43 条）

**需要**：在 **bakerydemo 自己的虚拟环境**中运行（需要 Django ORM）+ Playwright

脚本会自动切换到 bakerydemo 的 venv，直接运行即可：

```bash
python 数据驱动执行器/全自动执行.py
python 数据驱动执行器/全自动执行_扩展.py
python 数据驱动执行器/全自动执行_第三批.py
```

> ⚠️ 脚本会**自动备份数据、每个用例执行后恢复**，但仍建议先手动备份一次：
> ```bash
> cd bakerydemo
> copy bakerydemodb bakerydemodb.bak
> ```

**原理**：

```
备份数据 → 用 ORM 改数据（等效后台操作）→ Playwright 验证前台 → 自动恢复 → 下一个用例
```

**为什么这样做**：后台管理界面的 UI 自动化维护成本高（组件复杂、改版频繁），
而"改数据"这一步用 ORM 完成，"验证前台"用 Playwright 完成，是性价比最高的组合。

---

## 三、弱网测试（7 条）

```bash
python 弱网测试.py
```

通过 Chrome DevTools Protocol 模拟网络：

| 档位 | 延迟 | 带宽 |
|---|---|---|
| 无限速 | 0 ms | 不限 |
| Fast 3G | 150 ms | 1.5 Mbps |
| Slow 3G | 400 ms | 400 kbps |
| 断网 | — | — |

**注意**：CDP 的"不限速"必须传 `downloadThroughput: -1`，
传 `0` 表示 0 字节/秒（比 Slow 3G 还慢）。

---

## 四、性能测试（6 项）

**需要**：Locust

```bash
pip install locust
python 性能测试.py
```

该脚本会依次执行：

1. **单用户基准**：6 个主要页面的响应时间
2. **逐步加压**：5 → 10 → 20 → 40 并发，每次 15 秒
3. **静态资源分析**：CSS / JS 文件大小
4. **结果汇总**

也可以单独启动 Locust 的 Web 界面手动控制：

```bash
locust -f locustfile.py --host http://127.0.0.1:8000
```

> ⚠️ **重要**：被测对象是 Django 的 `runserver`（开发服务器），
> 不是生产级服务器。**性能数据只能作为本地基线**，不能据此判断真实承载能力。

---

## 通用注意事项

| 项目 | 说明 |
|---|---|
| **先起网站** | 所有脚本都要求 `http://127.0.0.1:8000` 可访问 |
| **数据安全** | 数据驱动类脚本会自动恢复；破坏性测试前请手动备份 |
| **依赖安装** | 这台机器的 pip 清华源缺少 playwright，请用官方源：`-i https://pypi.org/simple` |
| **中文路径** | 在 Git Bash 中运行需加 `MSYS_NO_PATHCONV=1`，否则 `/breads/` 会被转成 Windows 路径 |
