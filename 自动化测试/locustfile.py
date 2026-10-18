# -*- coding: utf-8 -*-
"""
Locust 压测脚本 —— 模拟普通访客浏览 bakerydemo

访问分布（按权重）：
    首页     4
    面包列表 3
    面包详情 2
    博客列表 2
    搜索     1
"""

from locust import HttpUser, task, between


class 浏览用户(HttpUser):
    """一个模拟访客：每隔 1-3 秒做一次操作"""

    wait_time = between(1, 3)

    @task(4)
    def 首页(self):
        self.client.get("/", name="首页")

    @task(3)
    def 面包列表(self):
        self.client.get("/breads/", name="面包列表")

    @task(2)
    def 面包详情(self):
        self.client.get("/breads/bagel/", name="面包详情")

    @task(2)
    def 博客列表(self):
        self.client.get("/blog/", name="博客列表")

    @task(1)
    def 搜索(self):
        self.client.get("/search/?q=bread", name="搜索")
