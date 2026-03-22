$(document).ready(function () {
    const stockDetailPanel = $("#stock-detail-content");
    const sourceSelect = $("#quote-source");
    const marketSelect = $("#overview-market");
    const heatmapContainer = $("#overview-heatmap");
    let currentCode = null;
    let currentRecommendations = [];

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
        const netMfAmount = flow.net_mf_amount || flow.buy_sm_amount || 0;
        const flowDate = flow.trade_date || "--";
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

        const html = `
            <div class="detail-grid">
                <div class="detail-item"><div class="label">股票</div><div class="value">${quote.name || code} (${code})</div></div>
                <div class="detail-item"><div class="label">现价</div><div class="value">${toFixed(quote.price)}</div></div>
                <div class="detail-item"><div class="label">涨跌幅</div><div class="value">${toFixed(quote.change_pct)}%</div></div>
                <div class="detail-item"><div class="label">成交量</div><div class="value">${toFixed(quote.volume, 0)}</div></div>
                <div class="detail-item"><div class="label">成交额</div><div class="value">${toFixed(quote.turnover, 0)}</div></div>
                <div class="detail-item"><div class="label">行情源</div><div class="value">${details.source || "--"}</div></div>
            </div>
            <div class="detail-grid">
                <div class="detail-item"><div class="label">资金流日期</div><div class="value">${flowDate}</div></div>
                <div class="detail-item"><div class="label">主力净流入</div><div class="value">${toFixed(netMfAmount, 2)}</div></div>
                <div class="detail-item"><div class="label">资金流状态</div><div class="value">${details.capital_flow_error || "正常"}</div></div>
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
        `;
        stockDetailPanel.html(html);
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

    function buildRecommendationCard(item) {
        const changeClass = item.change >= 0 ? "up" : "down";
        const tag = item.recommend_tag ? `<span class="recommend-tag">${item.recommend_tag}</span>` : "";
        return `
            <div class="stock-card clickable ${changeClass}" id="stock-${item.code}" data-code="${item.code}">
                <div class="stock-header">
                    <span class="stock-name">${item.name}</span>
                    <span class="stock-code">${item.code}</span>
                </div>
                ${tag}
                <div class="stock-price">${toFixed(item.price)}</div>
                <div class="stock-change">
                    <span class="change-amount">${item.change > 0 ? "+" : ""}${toFixed(item.change)}</span>
                    <span class="change-pct">(${toFixed(item.change_pct)}%)</span>
                </div>
                <div class="stock-details">
                    <div>市场：${item.market}</div>
                    <div>行业：${item.industry || "--"}</div>
                    <div>源：${item.source || "--"}</div>
                </div>
                <div class="stock-actions">
                    <button class="trade-btn action-btn" data-code="${item.code}" data-action="buy">Buy</button>
                    <button class="trade-btn action-btn" data-code="${item.code}" data-action="sell">Sell</button>
                    <button class="goto-news-btn btn-secondary action-btn" data-code="${item.code}" data-name="${item.name || ""}">资讯</button>
                </div>
            </div>
        `;
    }

    function marketLabel(market) {
        if (market === "A") {
            return "A股";
        }
        if (market === "HK") {
            return "港股";
        }
        if (market === "US") {
            return "美股";
        }
        return market || "未知市场";
    }

    function renderRecommendationsByMarket(groups, selector) {
        const wrapper = $(selector);
        wrapper.empty();
        const selectedMarket = marketSelect.val() || "ALL";
        const marketOrder = selectedMarket === "ALL" ? ["A", "HK", "US"] : [selectedMarket];
        let rendered = 0;
        marketOrder.forEach((market) => {
            const items = (groups && groups[market]) || [];
            if (!items.length) {
                return;
            }
            rendered += 1;
            const block = $(`
                <div class="market-recommend-block">
                    <h4 class="recommend-market-title">${marketLabel(market)}（${items.length}）</h4>
                    <div class="stock-grid"></div>
                </div>
            `);
            const grid = block.find(".stock-grid");
            items.forEach((item) => {
                grid.append(buildRecommendationCard(item));
            });
            wrapper.append(block);
        });
        if (!rendered) {
            wrapper.append('<div class="stock-card">暂无推荐数据</div>');
        }
    }

    function loadOverview() {
        const market = marketSelect.val() || "ALL";
        $.get(`/api/overview?market=${encodeURIComponent(market)}${getSourceQuery().replace("?", "&")}`, function (resp) {
            renderRecommendationsByMarket(resp.gainers_by_market || {}, "#stock-list-gainers");
            renderRecommendationsByMarket(resp.losers_by_market || {}, "#stock-list-losers");
            renderHeatmap(resp.heatmap || []);
            if (!currentCode && resp.recommendations && resp.recommendations.length > 0) {
                loadStockDetails(resp.recommendations[0].code);
            }
        });
    }

    $(document).on("click", ".trade-btn", function (e) {
        e.stopPropagation();
        const code = $(this).data("code");
        const action = $(this).data("action");
        window.location.href = `/trade?code=${code}&action=${action}`;
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

    sourceSelect.on("change", function () {
        loadOverview();
        if (currentCode) {
            loadStockDetails(currentCode);
        }
    });

    marketSelect.on("change", function () {
        currentCode = null;
        loadOverview();
    });

    loadOverview();
    setInterval(loadOverview, 8000);
});
