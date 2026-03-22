$(document).ready(function () {
    const pagination = $("#screener-pagination");
    const pageSizeSelect = $("#screener-page-size");
    const klineTitle = $("#screener-kline-title");
    const klineMeta = $("#screener-kline-meta");
    const klineContainer = document.getElementById("screener-kline-chart");
    const klineChart = window.createKlineChart ? window.createKlineChart(klineContainer) : null;
    let currentPage = 1;
    let activeFilters = {};
    let currentRows = [];
    let selectedKlineCode = "";

    function toNumber(value) {
        if (value === null || value === undefined || value === "") {
            return null;
        }
        const n = Number(value);
        return Number.isNaN(n) ? null : n;
    }

    function toFixed(value, digits = 2) {
        const n = Number(value);
        if (Number.isNaN(n)) {
            return "--";
        }
        return n.toFixed(digits);
    }

    function formatSourceLabel(source) {
        const token = (source || "").toString().toLowerCase();
        if (token === "eastmoney") {
            return "EastMoney";
        }
        if (token === "tickflow") {
            return "TickFlow";
        }
        if (token === "sina") {
            return "Sina";
        }
        if (token === "tencent") {
            return "Tencent";
        }
        return source || "自动";
    }

    function getFilters() {
        return {
            market: $("#screener-market").val(),
            source: $("#screener-source").val(),
            market_cap_min: toNumber($("#market-cap-min").val()),
            market_cap_max: toNumber($("#market-cap-max").val()),
            price_min: toNumber($("#price-min").val()),
            price_max: toNumber($("#price-max").val()),
            pe_max: toNumber($("#pe-max").val()),
            pb_max: toNumber($("#pb-max").val()),
            roe_min: toNumber($("#roe-min").val()),
            gross_margin_min: toNumber($("#gross-margin-min").val()),
            net_margin_min: toNumber($("#net-margin-min").val()),
        };
    }

    function renderPagination(page, totalPages) {
        pagination.empty();
        if (!totalPages || totalPages <= 1) {
            return;
        }
        const prevDisabled = page <= 1 ? "disabled" : "";
        const nextDisabled = page >= totalPages ? "disabled" : "";
        const html = `
            <button class="btn-secondary action-btn screener-page-btn" data-page="${page - 1}" ${prevDisabled}>上一页</button>
            <span>第 ${page} / ${totalPages} 页</span>
            <button class="btn-secondary action-btn screener-page-btn" data-page="${page + 1}" ${nextDisabled}>下一页</button>
        `;
        pagination.append(html);
    }

    function renderTable(items) {
        const tbody = $("#screener-table tbody");
        tbody.empty();
        if (!items || items.length === 0) {
            tbody.append('<tr><td colspan="17">暂无符合条件的股票</td></tr>');
            return;
        }
        items.forEach((item) => {
            const watchBtn = item.watchlist
                ? '<button class="btn-secondary action-btn" disabled>已在自选</button>'
                : `<button class="add-watch-btn btn-primary action-btn" data-code="${item.code}">加入自选</button>`;
            const newsBtn = `<button class="goto-news-btn btn-secondary action-btn" data-code="${item.code}" data-name="${item.name || ""}">资讯</button>`;
            const klineBtn = `<button class="view-kline-btn btn-secondary action-btn" data-code="${item.code}" data-name="${item.name || ""}">查看K线</button>`;
            const row = `
                <tr>
                    <td>${item.code}</td>
                    <td>${item.name}</td>
                    <td>${item.industry || "--"}</td>
                    <td>${toFixed(item.price)}</td>
                    <td class="${item.change_pct >= 0 ? "text-danger" : "text-success"}">${toFixed(item.change_pct)}%</td>
                    <td>${toFixed(item.pe)}</td>
                    <td>${toFixed(item.pb)}</td>
                    <td>${toFixed(item.roe)}%</td>
                    <td>${toFixed(item.gross_margin)}%</td>
                    <td>${toFixed(item.net_margin)}%</td>
                    <td>${toFixed(item.market_cap)}</td>
                    <td>${item.market || "--"}</td>
                    <td>${item.source || "--"}</td>
                    <td>${item.data_quality || "--"}</td>
                    <td class="screener-action-cell">${klineBtn}</td>
                    <td class="screener-action-cell">${watchBtn}</td>
                    <td class="screener-action-cell">${newsBtn}</td>
                </tr>
            `;
            tbody.append(row);
        });
    }

    function renderKline(items) {
        if (!klineChart || !window.LightweightCharts) {
            klineMeta.text("K线组件加载失败");
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
            klineChart.clear();
            klineMeta.text("暂无K线数据");
            return;
        }
        klineChart.setData(bars);
        klineMeta.text(`已加载 ${bars.length} 根日K`);
    }

    function loadKline(code, name) {
        if (!code) {
            return;
        }
        selectedKlineCode = code;
        const source = (activeFilters.source || "auto").toString();
        const sourceQuery = source && source !== "auto" ? `&source=${encodeURIComponent(source)}` : "";
        klineTitle.text(`行情K线 - ${name || code} (${code})`);
        klineMeta.text(`加载中（${formatSourceLabel(source)}）...`);
        $.get(`/api/stock/${encodeURIComponent(code)}/kline?limit=90${sourceQuery}`, function (resp) {
            renderKline((resp && resp.items) || []);
        }).fail(function () {
            if (klineChart) {
                klineChart.clear();
            }
            klineMeta.text("K线获取失败，请稍后重试");
        });
    }

    function runScreener(page = 1, useActiveFilters = false) {
        const pageSize = Number(pageSizeSelect.val() || 20);
        if (!useActiveFilters || !Object.keys(activeFilters).length) {
            activeFilters = getFilters();
        }
        currentPage = page;
        $("#screener-hint").text("筛选中...");
        $.ajax({
            url: "/api/screener",
            type: "POST",
            contentType: "application/json",
            data: JSON.stringify({ ...activeFilters, page: currentPage, page_size: pageSize }),
            success: function (resp) {
                currentRows = resp.items || [];
                renderTable(currentRows);
                const pageNo = resp.page || 1;
                const totalPages = resp.total_pages || 1;
                currentPage = pageNo;
                $("#screener-count").text(`${resp.count || 0} 只股票符合条件`);
                renderPagination(pageNo, totalPages);
                $("#screener-hint").text("筛选完成");
                if (currentRows.length === 0) {
                    if (klineChart) {
                        klineChart.clear();
                    }
                    klineTitle.text("行情K线");
                    klineMeta.text("当前条件下没有可展示的股票");
                    selectedKlineCode = "";
                    return;
                }
                const selectedRow = currentRows.find((item) => item.code === selectedKlineCode);
                if (selectedRow) {
                    loadKline(selectedRow.code, selectedRow.name);
                } else {
                    loadKline(currentRows[0].code, currentRows[0].name);
                }
            },
            error: function () {
                renderTable([]);
                $("#screener-count").text("0 只股票符合条件");
                pagination.empty();
                $("#screener-hint").text("筛选失败，请稍后重试");
                if (klineChart) {
                    klineChart.clear();
                }
                klineTitle.text("行情K线");
                klineMeta.text("筛选失败，无法加载K线");
            },
        });
    }

    $("#run-screener").on("click", function () {
        runScreener(1, false);
    });

    pageSizeSelect.on("change", function () {
        runScreener(1, true);
    });

    $(document).on("click", ".screener-page-btn", function () {
        const targetPage = Number($(this).data("page") || 1);
        if (targetPage < 1 || targetPage === currentPage) {
            return;
        }
        runScreener(targetPage, true);
    });

    $(document).on("click", ".add-watch-btn", function () {
        const code = $(this).data("code");
        const btn = $(this);
        btn.prop("disabled", true).text("添加中...");
        $.ajax({
            url: `/api/watchlist/${encodeURIComponent(code)}`,
            type: "POST",
            success: function () {
                btn.removeClass("btn-primary").addClass("btn-secondary").text("已在自选");
            },
            error: function () {
                btn.prop("disabled", false).text("加入自选");
            },
        });
    });

    $(document).on("click", ".goto-news-btn", function () {
        const code = ($(this).data("code") || "").toString().trim();
        const name = ($(this).data("name") || "").toString().trim();
        const query = encodeURIComponent(`${code} ${name}`.trim());
        window.location.href = `/watchlist-news?q=${query}&search_type=stock`;
    });

    $(document).on("click", ".view-kline-btn", function () {
        const code = ($(this).data("code") || "").toString().trim();
        const name = ($(this).data("name") || "").toString().trim();
        loadKline(code, name);
    });

    $("#screener-source").on("change", function () {
        if (selectedKlineCode) {
            const row = currentRows.find((item) => item.code === selectedKlineCode);
            loadKline(selectedKlineCode, row ? row.name : selectedKlineCode);
        }
    });

    runScreener(1, false);
});
