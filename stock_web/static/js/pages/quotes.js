$(document).ready(function () {
    const marketSelect = $("#quotes-market");
    const sourceSelect = $("#quotes-source");
    const keywordInput = $("#quotes-keyword");
    const searchBtn = $("#quotes-search-btn");
    const tbody = $("#quotes-table tbody");
    const countText = $("#quotes-count");
    const hintText = $("#quotes-hint");
    const detailTitle = $("#quotes-detail-title");
    const detailMeta = $("#quotes-detail-meta");
    const detailContent = $("#quotes-detail-content");
    const klineContainer = document.getElementById("quotes-kline-chart");
    let klineChart = null;
    let stockPool = [];
    let currentRows = [];
    let currentCode = "";
    let keywordTimer = null;
    let detailSeq = 0;
    let searchSeq = 0;

    function toFixed(value, digits = 2) {
        const n = Number(value);
        if (Number.isNaN(n)) {
            return "--";
        }
        return n.toFixed(digits);
    }

    function ensureKlineChart() {
        if (!klineChart && window.createKlineChart) {
            klineChart = window.createKlineChart(klineContainer);
        }
        return klineChart;
    }

    function resetDetail(message, showMeta) {
        detailContent.text(message || "");
        detailContent.addClass("quotes-detail-empty");
        detailMeta.text(showMeta || "点击列表中的“查看行情”");
        klineContainer.classList.add("is-empty");
        if (klineChart) {
            klineChart.clear();
        }
    }

    function getSourceQuery() {
        const source = (sourceSelect.val() || "auto").toString();
        if (!source || source === "auto") {
            return "";
        }
        return `?source=${encodeURIComponent(source)}`;
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
        return market || "--";
    }

    function updateRowQuote(code, quote) {
        const row = tbody
            .find("tr")
            .filter(function () {
                return (($(this).data("code") || "").toString().toUpperCase() === (code || "").toString().toUpperCase());
            })
            .first();
        if (!row.length) {
            return;
        }
        const priceCell = row.find(".quote-price");
        const changeCell = row.find(".quote-change");
        const sourceCell = row.find(".quote-source");
        if (!quote) {
            priceCell.text("--");
            changeCell.text("--");
            sourceCell.text("--");
            return;
        }
        priceCell.text(toFixed(quote.price));
        const pct = Number(quote.change_pct);
        changeCell.text(`${toFixed(pct)}%`);
        changeCell.removeClass("text-danger text-success");
        changeCell.addClass(pct >= 0 ? "text-danger" : "text-success");
        sourceCell.text(quote.source || "--");
    }

    function loadRowQuotes(items) {
        const sourceQuery = getSourceQuery();
        items.slice(0, 30).forEach((item) => {
            if (!item || !item.code) {
                return;
            }
            $.get(`/api/quote/${encodeURIComponent(item.code)}${sourceQuery}`, function (quote) {
                updateRowQuote(item.code, quote);
            }).fail(function () {
                updateRowQuote(item.code, null);
            });
        });
    }

    function renderRows(items) {
        tbody.empty();
        if (!items.length) {
            tbody.append('<tr><td colspan="8">没有匹配到股票</td></tr>');
            return;
        }
        items.forEach((item) => {
            const row = `
                <tr data-code="${item.code}" data-name="${item.name || item.code}">
                    <td>${item.code}</td>
                    <td>${item.name || item.code}</td>
                    <td>${marketLabel(item.market)}</td>
                    <td>${item.industry || "--"}</td>
                    <td class="quote-price">--</td>
                    <td class="quote-change">--</td>
                    <td class="quote-source">--</td>
                    <td><button class="view-quote-btn btn-secondary action-btn" data-code="${item.code}" data-name="${item.name || item.code}">查看行情</button></td>
                </tr>
            `;
            tbody.append(row);
        });
        loadRowQuotes(items);
    }

    function renderDetail(code, details) {
        const quote = (details && details.quote) || {};
        const flow = (details && details.capital_flow) || {};
        const financial = (details && details.financial_data) || {};
        const dailyBasic = financial.daily_basic || {};
        const indicator = financial.fina_indicator || {};
        const html = `
            <div class="detail-grid">
                <div class="detail-item"><div class="label">股票</div><div class="value">${quote.name || code} (${code})</div></div>
                <div class="detail-item"><div class="label">现价</div><div class="value">${toFixed(quote.price)}</div></div>
                <div class="detail-item"><div class="label">涨跌幅</div><div class="value">${toFixed(quote.change_pct)}%</div></div>
                <div class="detail-item"><div class="label">成交量</div><div class="value">${toFixed(quote.volume, 0)}</div></div>
                <div class="detail-item"><div class="label">成交额</div><div class="value">${toFixed(quote.turnover, 0)}</div></div>
                <div class="detail-item"><div class="label">来源</div><div class="value">${quote.source || "--"}</div></div>
            </div>
            <div class="detail-grid">
                <div class="detail-item"><div class="label">主力净流入</div><div class="value">${toFixed(flow.net_mf_amount, 2)}</div></div>
                <div class="detail-item"><div class="label">PE</div><div class="value">${toFixed(dailyBasic.pe, 2)}</div></div>
                <div class="detail-item"><div class="label">PB</div><div class="value">${toFixed(dailyBasic.pb, 2)}</div></div>
                <div class="detail-item"><div class="label">ROE</div><div class="value">${toFixed(indicator.roe, 2)}%</div></div>
                <div class="detail-item"><div class="label">毛利率</div><div class="value">${toFixed(indicator.grossprofit_margin, 2)}%</div></div>
                <div class="detail-item"><div class="label">净利率</div><div class="value">${toFixed(indicator.netprofit_margin, 2)}%</div></div>
            </div>
        `;
        detailContent.html(html);
        detailContent.removeClass("quotes-detail-empty");
    }

    function renderKline(items) {
        const chart = ensureKlineChart();
        if (!chart) {
            detailMeta.text("K线组件不可用");
            return;
        }
        const bars = (items || [])
            .map((item) => {
                const dateText = (item.date || "").toString().slice(0, 10);
                if (!dateText) {
                    return null;
                }
                return {
                    time: dateText,
                    open: Number(item.open || 0),
                    high: Number(item.high || 0),
                    low: Number(item.low || 0),
                    close: Number(item.close || 0),
                    volume: Number(item.volume || 0),
                };
            })
            .filter((item) => item && Number.isFinite(item.open) && Number.isFinite(item.high) && Number.isFinite(item.low) && Number.isFinite(item.close));
        if (!bars.length) {
            klineContainer.classList.add("is-empty");
            chart.clear();
            detailMeta.text("暂无K线数据");
            return;
        }
        klineContainer.classList.remove("is-empty");
        chart.setData(bars);
        detailMeta.text(`已加载 ${bars.length} 根日K`);
    }

    function loadKlineFallback(code, sourceQuery, seq) {
        const klineQuery = sourceQuery ? `${sourceQuery}&limit=120` : "?limit=120";
        $.get(`/api/stock/${encodeURIComponent(code)}/kline${klineQuery}`, function (resp) {
            if (seq !== detailSeq) {
                return;
            }
            renderKline((resp && resp.items) || []);
        }).fail(function () {
            if (seq !== detailSeq) {
                return;
            }
            if (klineChart) {
                klineChart.clear();
            }
            klineContainer.classList.add("is-empty");
            detailMeta.text("K线获取失败");
        });
    }

    function loadDetail(code, name) {
        if (!code) {
            return;
        }
        currentCode = code;
        detailSeq += 1;
        const seq = detailSeq;
        detailTitle.text(`股票行情详情 - ${name || code} (${code})`);
        detailMeta.text("加载中...");
        const sourceQuery = getSourceQuery();
        $.get(`/api/stock/${encodeURIComponent(code)}/details${sourceQuery}`, function (details) {
            if (seq !== detailSeq) {
                return;
            }
            const payload = details || {};
            renderDetail(code, payload);
            const dailyKlines = payload.daily_klines || [];
            if (dailyKlines.length) {
                renderKline(dailyKlines);
                return;
            }
            loadKlineFallback(code, sourceQuery, seq);
        }).fail(function () {
            if (seq !== detailSeq) {
                return;
            }
            if (klineChart) {
                klineChart.clear();
            }
            klineContainer.classList.add("is-empty");
            resetDetail("行情详情获取失败", "请稍后重试");
        });
    }

    function searchRows(preferLoadDetail) {
        const keywordRaw = (keywordInput.val() || "").toString().trim();
        const keyword = keywordRaw.toLowerCase();
        const rows = stockPool.filter((item) => {
            if (!keyword) {
                return true;
            }
            const code = (item.code || "").toString().toLowerCase();
            const name = (item.name || "").toString().toLowerCase();
            return code.includes(keyword) || name.includes(keyword);
        });
        currentRows = rows.slice(0, 100);
        renderRows(currentRows);
        countText.text(`${rows.length} 条`);
        if (!keyword) {
            hintText.text("点击“查看行情”加载详情与K线");
            return;
        }
        if (rows.length) {
            hintText.text("已命中本地股票池，支持快速查看与加入自选");
            if (preferLoadDetail && currentRows.length) {
                loadDetail(currentRows[0].code, currentRows[0].name);
            }
            return;
        }
        const seq = ++searchSeq;
        const market = marketSelect.val() || "ALL";
        hintText.text("本地未命中，正在进行在线搜索...");
        $.get(`/api/stocks/search?q=${encodeURIComponent(keywordRaw)}&market=${encodeURIComponent(market)}&limit=60`, function (items) {
            if (seq !== searchSeq) {
                return;
            }
            currentRows = (items || []).slice(0, 100);
            renderRows(currentRows);
            countText.text(`${currentRows.length} 条`);
            if (!currentRows.length) {
                hintText.text("在线搜索也未命中，请尝试更短关键字");
                return;
            }
            hintText.text("已展示在线搜索结果，可直接查看行情或加入自选");
            if (preferLoadDetail) {
                loadDetail(currentRows[0].code, currentRows[0].name);
            }
        }).fail(function () {
            if (seq !== searchSeq) {
                return;
            }
            hintText.text("在线搜索失败，请稍后重试");
        });
    }

    function loadStocks() {
        const market = marketSelect.val() || "ALL";
        hintText.text("加载中...");
        $.get(`/api/stocks?market=${encodeURIComponent(market)}`, function (items) {
            stockPool = items || [];
            const keywordRaw = (keywordInput.val() || "").toString().trim();
            searchRows(false);
            if (!currentRows.length) {
                if (keywordRaw) {
                    detailTitle.text("股票行情详情");
                    resetDetail("本地未命中，正在尝试在线搜索", "请稍候或点击搜索按钮");
                    currentCode = "";
                    return;
                }
                detailTitle.text("股票行情详情");
                resetDetail("当前条件暂无股票", "请切换市场或搜索关键字");
                currentCode = "";
                return;
            }
            const selected = currentRows.find((item) => item.code === currentCode);
            if (selected) {
                loadDetail(selected.code, selected.name);
            } else {
                loadDetail(currentRows[0].code, currentRows[0].name);
            }
        }).fail(function () {
            stockPool = [];
            currentRows = [];
            renderRows([]);
            countText.text("0 条");
            hintText.text("股票列表加载失败");
            detailTitle.text("股票行情详情");
            resetDetail("股票列表加载失败", "请稍后重试");
        });
    }

    searchBtn.on("click", function () {
        searchRows(true);
    });

    keywordInput.on("keydown", function (event) {
        if (event.key === "Enter") {
            searchRows(true);
        }
    });

    keywordInput.on("input", function () {
        if (keywordTimer) {
            clearTimeout(keywordTimer);
        }
        keywordTimer = setTimeout(function () {
            searchRows(false);
        }, 220);
    });

    marketSelect.on("change", function () {
        loadStocks();
    });

    sourceSelect.on("change", function () {
        renderRows(currentRows);
        if (currentCode) {
            const selected = currentRows.find((item) => item.code === currentCode);
            loadDetail(currentCode, selected ? selected.name : currentCode);
        }
    });

    $(document).on("click", ".view-quote-btn", function () {
        const code = ($(this).data("code") || "").toString().trim();
        const name = ($(this).data("name") || "").toString().trim();
        loadDetail(code, name);
    });

    resetDetail("请先从上方列表选择股票", "点击列表中的“查看行情”");
    loadStocks();
});
