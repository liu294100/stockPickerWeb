(function () {
    function createKlineChart(container) {
        if (!container || !window.LightweightCharts) {
            return null;
        }
        try {
            const chart = LightweightCharts.createChart(container, {
                layout: {
                    background: { color: "#ffffff" },
                    textColor: "#475569",
                },
                rightPriceScale: {
                    borderColor: "#e2e8f0",
                },
                timeScale: {
                    borderColor: "#e2e8f0",
                    timeVisible: true,
                },
                grid: {
                    vertLines: { color: "#f1f5f9" },
                    horzLines: { color: "#f1f5f9" },
                },
                crosshair: {
                    mode: LightweightCharts.CrosshairMode ? LightweightCharts.CrosshairMode.Normal : 0,
                },
            });
            const candleOptions = {
                upColor: "#ef4444",
                downColor: "#10b981",
                borderVisible: false,
                wickUpColor: "#ef4444",
                wickDownColor: "#10b981",
            };
            const volumeOptions = {
                priceFormat: { type: "volume" },
                priceScaleId: "",
                color: "#94a3b8",
            };
            const candlestickSeries = typeof chart.addCandlestickSeries === "function"
                ? chart.addCandlestickSeries(candleOptions)
                : chart.addSeries(LightweightCharts.CandlestickSeries, candleOptions);
            const volumeSeries = typeof chart.addHistogramSeries === "function"
                ? chart.addHistogramSeries(volumeOptions)
                : chart.addSeries(LightweightCharts.HistogramSeries, volumeOptions);
            if (volumeSeries && volumeSeries.priceScale) {
                volumeSeries.priceScale().applyOptions({
                    scaleMargins: { top: 0.82, bottom: 0 },
                });
            }
            if (candlestickSeries && candlestickSeries.priceScale) {
                candlestickSeries.priceScale().applyOptions({
                    scaleMargins: { top: 0.1, bottom: 0.24 },
                });
            }
            const resizeChart = function () {
                const width = container.clientWidth || 600;
                const height = container.clientHeight || 360;
                chart.resize(width, height);
            };
            const normalizeTime = function (value) {
                if (!value) {
                    return null;
                }
                if (typeof value === "number" && Number.isFinite(value)) {
                    return value;
                }
                const dateText = String(value).slice(0, 10);
                const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(dateText);
                if (!match) {
                    return null;
                }
                return {
                    year: Number(match[1]),
                    month: Number(match[2]),
                    day: Number(match[3]),
                };
            };
            const sanitizeBars = function (bars) {
                const map = new Map();
                (bars || []).forEach((bar) => {
                    const time = normalizeTime(bar && bar.time);
                    const open = Number(bar && bar.open);
                    const high = Number(bar && bar.high);
                    const low = Number(bar && bar.low);
                    const close = Number(bar && bar.close);
                    const volume = Number(bar && bar.volume);
                    if (!time) {
                        return;
                    }
                    if (!Number.isFinite(open) || !Number.isFinite(high) || !Number.isFinite(low) || !Number.isFinite(close)) {
                        return;
                    }
                    if (high < low) {
                        return;
                    }
                    const key = typeof time === "number" ? String(time) : `${time.year}-${time.month}-${time.day}`;
                    map.set(key, {
                        time,
                        open,
                        high,
                        low,
                        close,
                        volume: Number.isFinite(volume) ? volume : 0,
                    });
                });
                return Array.from(map.values()).sort((a, b) => {
                    const ta = typeof a.time === "number" ? a.time : Date.UTC(a.time.year, a.time.month - 1, a.time.day);
                    const tb = typeof b.time === "number" ? b.time : Date.UTC(b.time.year, b.time.month - 1, b.time.day);
                    return ta - tb;
                });
            };
            resizeChart();
            window.addEventListener("resize", resizeChart);
            return {
                setData: function (bars) {
                    if (!candlestickSeries || !volumeSeries) {
                        return;
                    }
                    const safeBars = sanitizeBars(bars);
                    candlestickSeries.setData(safeBars);
                    volumeSeries.setData(
                        safeBars.map((bar) => ({
                            time: bar.time,
                            value: Number(bar.volume || 0),
                            color: bar.close >= bar.open ? "rgba(239,68,68,0.5)" : "rgba(16,185,129,0.5)",
                        }))
                    );
                    if (safeBars.length) {
                        chart.timeScale().fitContent();
                    }
                },
                clear: function () {
                    if (!candlestickSeries || !volumeSeries) {
                        return;
                    }
                    candlestickSeries.setData([]);
                    volumeSeries.setData([]);
                },
            };
        } catch (error) {
            return null;
        }
    }
    window.createKlineChart = createKlineChart;
})();
