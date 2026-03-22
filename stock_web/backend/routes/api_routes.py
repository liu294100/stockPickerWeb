from flask import request, jsonify


def register_api_routes(app, services):
    @app.route("/api/quote/<code>")
    def get_quote(code):
        source = request.args.get("source")
        if source == "auto":
            source = None
        quote = services.market_service.get_quote(code, source=source)
        if quote:
            return jsonify(quote)
        return jsonify({"error": "Stock not found"}), 404

    @app.route("/api/stocks")
    def get_stocks():
        market = request.args.get("market")
        watchlist_only = request.args.get("watchlist") == "1"
        return jsonify(services.market_service.get_stock_pool(market=market, watchlist_only=watchlist_only))

    @app.route("/api/stocks", methods=["POST"])
    def upsert_stock():
        payload = request.json or {}
        stock, error = services.market_service.upsert_stock(payload)
        if error:
            return jsonify({"error": error}), 400
        return jsonify(stock)

    @app.route("/api/stocks/<code>", methods=["PUT"])
    def patch_stock(code):
        payload = request.json or {}
        stock, error = services.market_service.patch_stock(code, payload)
        if error:
            return jsonify({"error": error}), 400
        return jsonify(stock)

    @app.route("/api/stocks/<code>", methods=["DELETE"])
    def delete_stock(code):
        success = services.market_service.delete_stock(code)
        if not success:
            return jsonify({"error": "Stock not found"}), 404
        return jsonify({"message": "deleted"})

    @app.route("/api/watchlist", methods=["GET"])
    def get_watchlist():
        market = request.args.get("market")
        return jsonify(services.market_service.get_stock_pool(market=market, watchlist_only=True))

    @app.route("/api/watchlist/<code>", methods=["POST"])
    def add_watchlist(code):
        success = services.market_service.set_watchlist(code, True)
        if not success:
            return jsonify({"error": "Stock not found"}), 404
        return jsonify({"message": "added"})

    @app.route("/api/watchlist/<code>", methods=["DELETE"])
    def remove_watchlist(code):
        success = services.market_service.set_watchlist(code, False)
        if not success:
            return jsonify({"error": "Stock not found"}), 404
        return jsonify({"message": "removed"})

    @app.route("/api/overview")
    def get_overview():
        market = request.args.get("market")
        source = request.args.get("source")
        if source == "auto":
            source = None
        watchlist_only = request.args.get("watchlist") == "1"
        data = services.market_service.get_overview(market=market, source=source, watchlist_only=watchlist_only)
        return jsonify(data)

    @app.route("/api/stock/<code>/details")
    def get_stock_details(code):
        source = request.args.get("source")
        if source == "auto":
            source = None
        details = services.market_service.get_stock_details(code, source=source)
        if not details.get("quote"):
            return jsonify({"error": "Stock not found"}), 404
        return jsonify(details)

    @app.route("/api/news")
    def get_news():
        source = request.args.get("source")
        query = request.args.get("q")
        search_type = request.args.get("search_type")
        mode = request.args.get("mode")
        limit = request.args.get("limit", type=int) or 30
        data = services.market_service.search_news(
            source=source,
            query=query,
            search_type=search_type,
            mode=mode,
            limit=limit,
        )
        return jsonify(data)

    @app.route("/api/news/sources")
    def get_news_sources():
        return jsonify(services.market_service.get_news_sources())

    @app.route("/api/screener", methods=["POST"])
    def run_screener():
        filters = request.json or {}
        page = filters.get("page", 1)
        page_size = filters.get("page_size", 20)
        try:
            page = int(page)
        except (TypeError, ValueError):
            page = 1
        try:
            page_size = int(page_size)
        except (TypeError, ValueError):
            page_size = 20
        page = max(page, 1)
        page_size = max(5, min(page_size, 100))
        result = services.market_service.screen_stocks(filters)
        total = len(result)
        total_pages = max(1, (total + page_size - 1) // page_size)
        page = min(page, total_pages)
        start = (page - 1) * page_size
        end = start + page_size
        paged_items = result[start:end]
        return jsonify({"count": total, "items": paged_items, "page": page, "page_size": page_size, "total_pages": total_pages})

    @app.route("/api/account")
    def get_account():
        return jsonify(services.trade_service.get_account_info())

    @app.route("/api/trade/buy", methods=["POST"])
    def buy_stock():
        data = request.json or {}
        code = data.get("code")
        quantity = data.get("quantity")
        if not code or not quantity:
            return jsonify({"error": "Missing code or quantity"}), 400
        success, message = services.trade_service.buy(code, int(quantity))
        if success:
            return jsonify({"message": message})
        return jsonify({"error": message}), 400

    @app.route("/api/trade/sell", methods=["POST"])
    def sell_stock():
        data = request.json or {}
        code = data.get("code")
        quantity = data.get("quantity")
        if not code or not quantity:
            return jsonify({"error": "Missing code or quantity"}), 400
        success, message = services.trade_service.sell(code, int(quantity))
        if success:
            return jsonify({"message": message})
        return jsonify({"error": message}), 400

    @app.route("/api/notify/test", methods=["POST"])
    def test_notify():
        data = request.json or {}
        message = data.get("message", "Test notification")
        channels = data.get("channels", ["wechat"])
        return jsonify(services.notification_service.send_test(message, channels))
