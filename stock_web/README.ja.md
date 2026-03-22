# Stock Assistant Web

Stock Assistant Web は、Flask ベースの株式分析・仮想売買アプリです。  
デスクトップ GUI 版から Web 版へ移行し、複数ページ構成と通知機能を提供します。

## 言語ドキュメント

- English（デフォルト）: [README.md](README.md)
- 中文: [README.zh-CN.md](README.zh-CN.md)
- 日本語: [README.ja.md](README.ja.md)

## プロジェクト概要

主な機能は以下です：

- マーケット概要（A株 / 香港株 / 米国株）
- ウォッチリスト管理
- ニュース・センチメント表示
- スクリーナー（ページネーション対応）
- 仮想売買（買い / 売り / ポジション管理）
- 通知センターと設定画面

## 主要機能

- リアルタイム価格取得（フォールバック対応）
- 市場別の上昇・下落銘柄表示
- ニュースのタイムライン表示
- 各ページからのウォッチリスト追加とニュース遷移
- 損益トラッキング
- 通知連携：
  - PushPlus
  - Twilio WhatsApp
  - Telegram

## 技術スタック

- Python
- Flask
- SQLite（ローカル永続化）
- Vanilla JS + jQuery
- HTML テンプレート + CSS

## 実行方法

### 方法 A：ワンクリック起動（推奨）

Windows:

```bat
run.bat
```

起動スクリプトが自動で：

- Python を検出
- 複数ある場合は番号選択
- 依存関係を自動インストール
- アプリを起動
- Python 未インストール時はダウンロードリンクを表示

Linux / macOS:

```bash
bash run.sh
```

### 方法 B：手動起動

1) 依存関係をインストール：

```bash
python -m pip install -r requirements.txt
```

2) アプリ起動：

```bash
python app.py
```

3) ブラウザでアクセス：

`http://127.0.0.1:5000`

## 設定

設定ページで以下を構成できます：

- Tushare トークン
- PushPlus トークン
- Twilio 認証情報・電話番号
- Telegram Bot トークン / Chat ID

## ディレクトリ構成

- `app.py`: Flask エントリーポイント
- `backend/`: ルーティングとサービス層
- `core/`: ビジネスロジック
- `templates/`: HTML テンプレート
- `static/`: フロントエンド資産
- `data/`: 設定と SQLite データ
- `run.bat` / `run_windows.ps1` / `run.sh`: 起動スクリプト
