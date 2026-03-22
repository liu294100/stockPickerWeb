from flask import render_template, request, jsonify


def register_page_routes(app, services):
    @app.route("/", endpoint="index")
    def index():
        return render_template("index.html")

    @app.route("/screener", endpoint="screener_page")
    def screener_page():
        return render_template("screener.html")

    @app.route("/quotes", endpoint="quotes_page")
    def quotes_page():
        return render_template("quotes.html")

    @app.route("/trade", endpoint="trade_page")
    def trade_page():
        return render_template("trade.html")

    @app.route("/watchlist", endpoint="watchlist_page")
    def watchlist_page():
        return render_template("watchlist.html")

    @app.route("/news", endpoint="news_page")
    def news_page():
        return render_template("news.html", news_mode="all", news_page_title="资讯舆情", news_page_hint="聚合市场热点，辅助你更快判断板块轮动。")

    @app.route("/watchlist-news", endpoint="watchlist_news_page")
    def watchlist_news_page():
        return render_template("news.html", news_mode="watchlist", news_page_title="自选股资讯", news_page_hint="聚焦自选股票相关新闻，支持来源筛选与多方式搜索。")

    @app.route("/notify-center", endpoint="notify_center_page")
    def notify_center_page():
        return render_template("notify_center.html")

    @app.route("/settings", methods=["GET", "POST"], endpoint="settings_page")
    def settings_page():
        if request.method == "POST":
            data = request.json or {}
            services.settings_service.update_settings(data)
            return jsonify({"message": "Settings saved"})
        return render_template("settings.html", config=services.settings_service.get_config())
