# Stock Assistant Web

Stock Assistant Web 是一个基于 Flask 的股票分析与模拟交易项目。  
它由原桌面 GUI 版本迁移为 Web 版本，提供多页面操作和消息通知能力。

## 语言版本

- English（默认）: [README.md](README.md)
- 中文: [README.zh-CN.md](README.zh-CN.md)
- 日本語: [README.ja.md](README.ja.md)

## 项目介绍

项目包含以下核心模块：

- 市场总览（A股/港股/美股）
- 自选池管理
- 资讯舆情聚合
- 策略选股（支持分页）
- 模拟交易（买入/卖出/持仓）
- 消息中心与系统设置

## 主要功能

- 实时行情抓取与数据源降级兜底
- 按市场展示涨跌幅推荐
- 资讯时间线展示
- 各页面一键加入自选和资讯跳转
- 交易盈亏统计
- 通知渠道配置：
  - PushPlus
  - Twilio WhatsApp
  - Telegram

## 技术栈

- Python
- Flask
- SQLite（本地持久化）
- Vanilla JS + jQuery
- HTML 模板 + CSS

## 使用方式

### 方式 A：一键脚本（推荐）

Windows：

```bat
run.bat
```

脚本会自动：

- 检测本机 Python
- 多版本时按序号选择
- 自动安装依赖
- 启动项目
- 未安装 Python 时给出官方下载链接

Linux / macOS：

```bash
bash run.sh
```

### 方式 B：手动启动

1）安装依赖：

```bash
python -m pip install -r requirements.txt
```

2）启动服务：

```bash
python app.py
```

3）浏览器访问：

`http://127.0.0.1:5000`

## 配置说明

在“系统设置”页面中可配置：

- Tushare Token
- PushPlus Token
- Twilio 账号与号码
- Telegram Bot Token / Chat ID

## 目录结构

- `app.py`：Flask 启动入口
- `backend/`：路由与服务层
- `core/`：核心业务逻辑
- `templates/`：页面模板
- `static/`：前端资源
- `data/`：配置与数据库
- `run.bat`、`run_windows.ps1`、`run.sh`：启动脚本
