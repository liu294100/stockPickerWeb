# Stock Assistant Web

这是从 `daisuostock_pro_fixed.py` GUI 版本迁移到 Flask 的 Web 版本，支持多菜单页面与消息推送。

## 功能

- 实时行情：新浪/腾讯接口，失败自动降级模拟行情
- 模拟交易：买入、卖出、持仓与盈亏统计
- 消息推送：微信（PushPlus）、WhatsApp（Twilio）、Telegram
- 多菜单界面：市场总览、自选池、资讯舆情、交易中心、消息中心、系统设置

## Python 3.13 路径使用

你提供的 Python 路径是：

`E:\program files\Python\Python313`

建议直接使用完整解释器路径运行，避免系统 PATH 冲突。

1. 安装依赖

```bash
"E:\program files\Python\Python313\python.exe" -m pip install -r requirements.txt
```

2. 启动应用

```bash
"E:\program files\Python\Python313\python.exe" app.py
```

3. 浏览器访问

`http://127.0.0.1:5000`

## 配置项

在“系统设置”页面可配置：

- Tushare Token
- 微信 PushPlus Token
- WhatsApp SID / Token / 发送号 / 接收号
- Telegram Bot Token / Chat ID

## 目录结构

- `app.py`：Flask 主入口
- `core/`：业务逻辑
  - `data_fetcher.py`：行情获取
  - `trade_engine.py`：交易引擎
  - `notification.py`：推送渠道
  - `config_manager.py`：配置管理
- `templates/`：页面模板
- `static/`：CSS 与 JavaScript
- `data/`：配置与交易数据
