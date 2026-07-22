# Apple 官翻 Mac mini 库存监控

自动监控 Apple 中国官翻商店 Mac mini 库存，有货时通过 PushPlus 推送微信通知。

## 功能
- 每 30 分钟自动检查 Apple 官翻页面
- 检测到 Mac mini 有货时，自动推送微信通知（含产品名称、价格、购买链接）
- 运行在 GitHub Actions 上，不需要本地电脑开机

## 配置
需要设置 Repository Secret: `PUSHPLUS_TOKEN`
