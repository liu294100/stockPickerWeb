$(document).ready(function () {
    const stockDetailPanel = $("#stock-detail-content");
    const sourceSelect = $("#quote-source");
    const marketSelect = $("#watchlist-market");
    const heatmapContainer = $("#watchlist-heatmap");
    let currentCode = null;

    function getSourceQuery() {
        const selected = sourceSelect.val();
        if (!selected || selected === "auto") {
            return "";
        }
        return `?source=${encodeURIComponent(selected)}`;
    }

    function toFixed(value, digits = 2) {
        if (value === null || value === undefined || Number.isNaN(Number(value))) {
            return "--";
        }
        return Number(value).toFixed(digits);
    }

    function renderDetail(code, details) {
        const quote = details.quote || {};
        const flow = details.capital_flow || {};
        const financial = details.financial_data || {};
        const dailyBasic = financial.daily_basic || {};
        const indicator = financial.fina_indicator || {};
        const klines = details.daily_klines || [];
        const klineRows = klines
            .slice(-5)
            .reverse()
            .map(
                (row) => `
                    <tr>
                        <td>${row.date || "--"}</td>
                        <td>${toFixed(row.open)}</td>
                        <td>${toFixed(row.close)}</td>
                        <td>${toFixed(row.high)}</td>
                        <td>${toFixed(row.low)}</td>
                        <td>${toFixed(row.volume, 0)}</td>
                    </tr>
                `
            )
            .join("");

        stockDetailPanel.html(`
            <div class="detail-grid">
                <div class="detail-item"><div class="label">股票</div><div class="value">${quote.name || code} (${code})</div></div>
                <div class="detail-item"><div class="label">现价</div><div class="value">${toFixed(quote.price)}</div></div>
                <div class="detail-item"><div class="label">涨跌额</div><div class="value">${toFixed(quote.change)}</div></div>
                <div class="detail-item"><div class="label">涨跌幅</div><div class="value">${toFixed(quote.change_pct)}%</div></div>
                <div class="detail-item"><div class="label">成交额</div><div class="value">${toFixed(quote.turnover, 0)}</div></div>
                <div class="detail-item"><div class="label">行情源</div><div class="value">${details.source || "--"}</div></div>
            </div>
            <div class="detail-grid">
                <div class="detail-item"><div class="label">资金流状态</div><div class="value">${details.capital_flow_error || "正常"}</div></div>
                <div class="detail-item"><div class="label">资金流日期</div><div class="value">${flow.trade_date || "--"}</div></div>
            </div>
            <div class="detail-grid">
                <div class="detail-item"><div class="label">估值日期</div><div class="value">${dailyBasic.trade_date || "--"}</div></div>
                <div class="detail-item"><div class="label">市盈率PE</div><div class="value">${toFixed(dailyBasic.pe, 2)}</div></div>
                <div class="detail-item"><div class="label">市净率PB</div><div class="value">${toFixed(dailyBasic.pb, 2)}</div></div>
                <div class="detail-item"><div class="label">总市值</div><div class="value">${toFixed(dailyBasic.total_mv, 2)}</div></div>
                <div class="detail-item"><div class="label">ROE</div><div class="value">${toFixed(indicator.roe, 2)}%</div></div>
                <div class="detail-item"><div class="label">毛利率</div><div class="value">${toFixed(indicator.grossprofit_margin, 2)}%</div></div>
                <div class="detail-item"><div class="label">财务数据状态</div><div class="value">${details.financial_data_error || "正常"}</div></div>
            </div>
            <div class="detail-kline">
                <strong>最近5个交易日日K</strong>
                <table>
                    <thead>
                        <tr><th>日期</th><th>开</th><th>收</th><th>高</th><th>低</th><th>量</th></tr>
                    </thead>
                    <tbody>
                        ${klineRows || '<tr><td colspan="6">暂无日K数据</td></tr>'}
                    </tbody>
                </table>
            </div>
        `);
    }

    function loadStockDetails(code) {
        currentCode = code;
        stockDetailPanel.html("加载中...");
        $.get(`/api/stock/${code}/details${getSourceQuery()}`, function (details) {
            renderDetail(code, details);
        }).fail(function (xhr) {
            const msg = xhr.responseJSON && xhr.responseJSON.error ? xhr.responseJSON.error : "详情获取失败";
            stockDetailPanel.html(msg);
        });
    }

    function colorClass(value) {
        if (value >= 3) {
            return "heat-hot";
        }
        if (value > 0) {
            return "heat-warm";
        }
        if (value <= -3) {
            return "heat-cold";
        }
        return "heat-cool";
    }

    function renderHeatmap(items) {
        heatmapContainer.empty();
        if (!items || items.length === 0) {
            heatmapContainer.append('<div class="heatmap-item heat-cool">暂无热力图数据</div>');
            return;
        }
        items.forEach((item) => {
            const html = `
                <div class="heatmap-item ${colorClass(item.value)}">
                    <div class="heatmap-label">${item.label}</div>
                    <div class="heatmap-value">${toFixed(item.value)}%</div>
                </div>
            `;
            heatmapContainer.append(html);
        });
    }

    function renderWatchlist(stocks) {
        const grid = $("#watchlist-grid");
        grid.empty();
        (stocks || []).forEach((item) => {
            const html = `
                <div class="stock-card clickable" id="pool-${item.code}" data-code="${item.code}" data-name="${item.name}" data-industry="${item.industry}" data-market="${item.market}">
                    <div class="stock-header">
                        <span class="stock-name">${item.name}</span>
                        <span class="stock-code">${item.code}</span>
                    </div>
                    <div class="stock-details">
                        <div>行业：${item.industry}</div>
                        <div>市场：${item.market}</div>
                    </div>
                    <div class="stock-actions">
                        <button class="go-trade-btn action-btn" data-code="${item.code}">去交易</button>
                        <button class="goto-news-btn btn-secondary action-btn" data-code="${item.code}" data-name="${item.name || ""}">资讯</button>
                        <button class="edit-stock-btn btn-secondary action-btn" data-code="${item.code}">编辑</button>
                        <button class="remove-watch-btn btn-danger action-btn" data-code="${item.code}">移除</button>
                    </div>
                </div>
            `;
            grid.append(html);
        });
        if (stocks && stocks.length > 0) {
            loadStockDetails(stocks[0].code);
        } else {
            stockDetailPanel.html("暂无自选股票，请先新增或加入自选。");
        }
    }

    function loadWatchlist() {
        const market = marketSelect.val() || "ALL";
        $.get(`/api/watchlist?market=${encodeURIComponent(market)}`, function (stocks) {
            renderWatchlist(stocks);
        });
        $.get(`/api/overview?watchlist=1&market=${encodeURIComponent(market)}${getSourceQuery().replace("?", "&")}`, function (resp) {
            renderHeatmap(resp.heatmap || []);
        });
    }

    $(document).on("click", ".go-trade-btn", function (e) {
        e.stopPropagation();
        const code = $(this).data("code");
        window.location.href = `/trade?code=${code}`;
    });

    $(document).on("click", ".goto-news-btn", function (e) {
        e.stopPropagation();
        const code = ($(this).data("code") || "").toString().trim();
        const name = ($(this).data("name") || "").toString().trim();
        const query = encodeURIComponent(`${code} ${name}`.trim());
        window.location.href = `/watchlist-news?q=${query}&search_type=stock`;
    });

    $(document).on("click", ".stock-card.clickable", function () {
        const code = $(this).data("code");
        loadStockDetails(code);
    });

    $(document).on("click", ".remove-watch-btn", function (e) {
        e.stopPropagation();
        const code = $(this).data("code");
        $.ajax({
            url: `/api/watchlist/${encodeURIComponent(code)}`,
            type: "DELETE",
            success: function () {
                loadWatchlist();
            },
        });
    });

    $(document).on("click", ".edit-stock-btn", function (e) {
        e.stopPropagation();
        const card = $(this).closest(".stock-card");
        $("#stock-editor").show();
        $("#stock-code-input").val(card.data("code"));
        $("#stock-name-input").val(card.data("name"));
        $("#stock-industry-input").val(card.data("industry"));
        $("#stock-market-input").val(card.data("market"));
        $("#stock-form-hint").text("编辑模式：保存后将更新现有股票信息。");
    });

    $("#open-stock-form").on("click", function () {
        $("#stock-editor").show();
        $("#stock-code-input").val("");
        $("#stock-name-input").val("");
        $("#stock-industry-input").val("");
        $("#stock-market-input").val("A");
        $("#stock-form-hint").text("新增模式：自动加入自选池。");
    });

    $("#cancel-stock-btn").on("click", function () {
        $("#stock-editor").hide();
    });

    $("#save-stock-btn").on("click", function () {
        const payload = {
            code: ($("#stock-code-input").val() || "").trim().toUpperCase(),
            name: ($("#stock-name-input").val() || "").trim(),
            industry: ($("#stock-industry-input").val() || "").trim(),
            market: $("#stock-market-input").val(),
            watchlist: true,
        };
        if (!payload.code || !payload.name) {
            $("#stock-form-hint").text("代码和名称必填");
            return;
        }
        $.ajax({
            url: "/api/stocks",
            type: "POST",
            contentType: "application/json",
            data: JSON.stringify(payload),
            success: function () {
                $("#stock-form-hint").text("保存成功");
                loadWatchlist();
            },
            error: function () {
                $("#stock-form-hint").text("保存失败");
            },
        });
    });

    sourceSelect.on("change", function () {
        if (currentCode) {
            loadStockDetails(currentCode);
        }
        loadWatchlist();
    });

    marketSelect.on("change", function () {
        loadWatchlist();
    });

    loadWatchlist();
});
