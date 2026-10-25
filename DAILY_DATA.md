# 每日公开真实数据

网页：https://yxt1017.github.io/market-opportunity-radar/

## 自动更新

GitHub Actions 工作流 `Daily public data and Pages` 每天北京时间 **11:23**（03:23 UTC）执行。无需本机开机。也可以在仓库 Actions → Daily public data and Pages → Run workflow 手动运行。定时调度可能延迟，不保证精确到分钟。公开仓库长时间无活动时 GitHub 可能停用定时任务；网页超过36小时没有新采集会提示检查任务。

流程先运行测试，再读取官方公开接口，保存90天历史，最后重新发布 Pages。失败来源不补零、不填模拟数据；保留旧观测的原日期，在网页来源页显示失败。部分失败时仍发布可用数据及错误状态，并将本轮工作流标记失败。

## 已接入范围

- Wikimedia Analytics API：16个中文维基百科条目的每日 `all-access / user` 阅读次数；回填最近35日，每次更新校正该窗口内的官方值。阅读数据按 UTC 自然日统计，存在公布延迟和中文读者覆盖偏差。单条目的规范标题、跳转合并规则与地区语言偏差使其不等于全网关注。
- GitHub REST API：6个公开软件项目的 `stargazers_count` 累计Star数；按北京时间每日保存快照。从接入当天开始积累历史，未伪造此前快照。同一天重跑覆盖当天快照。

观察清单由人工选择，见 `config/public_watchlist.json`。这是公开关注信号，**不是闲鱼、小红书、拼多多的真实搜索量、销量、利润或付费用户数**，也不是自动发现全网新词。

官方定义：
- https://doc.wikimedia.org/generated-data-platform/aqs/analytics-api/concepts/page-views.html
- https://doc.wikimedia.org/generated-data-platform/aqs/analytics-api/examples/page-metrics.html
- https://docs.github.com/en/rest/activity/starring

## 排名与时间

百科榜只比较百科阅读量：每个条目以其最新已公布的观测日为锚点，最近7日均值对比此前7日均值，每段至少5天、前期均值大于0才计算；缺失日不补零。超过3天未有新观测，或本轮该来源失败，暂停排名。

GitHub榜只比较GitHub数据：需要相隔7天的两次累计Star快照才计算7日净变化率；只有相邻两个自然日都有快照才显示日净变化。首次接入显示“历史积累中”。Star撤销也计入净变化。超过1天未有新快照，或本轮来源失败，暂停排名。

两类指标分别排名，不把累计Star与每日阅读量混为一个热度分数。公开区与用户本地导入区、模拟演示区分开。

## 存储和权限

- `docs/data/public.json`：公开统计快照与来源信息，压缩去重但保留原始值、观测日期、抓取时间、API URL和响应摘要。
- 用户手工导入记录仍保存在浏览器，不自动上传。
- 使用GitHub每次运行签发的临时令牌，无需个人永久密钥。采集任务仅有本仓库内容写入权限，实际提交路径为 `docs/data/public.json`；发布任务仅有Pages写入和临时部署身份权限。
- Pages 的发布源需设为 **GitHub Actions**，由同一流程发布。仅由机器人提交文件不会触发原先的分支型Pages构建。
- 停用：Actions → Daily public data and Pages → Disable workflow。

## 本机运行与测试

```text
python scripts/update_public_data.py
python -m unittest discover -s tests
node tests/test_web.cjs
node tests/test_public.cjs
```

数据采集只依赖 Python 标准库。联网时可省略 GITHUB_TOKEN，GitHub匿名调用有额度限制。这个新增每日公开数据功能服务于网页版；原Python界面继续用于本地手工导入。
