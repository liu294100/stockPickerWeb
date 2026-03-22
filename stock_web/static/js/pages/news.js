$(document).ready(function () {
    const newsList = $("#news-list");
    const sourceSelect = $("#news-source");
    const searchTypeSelect = $("#news-search-type");
    const queryInput = $("#news-query");
    const searchBtn = $("#news-search-btn");
    const resetBtn = $("#news-reset-btn");
    const mode = newsList.data("mode") || "all";
    const urlParams = new URLSearchParams(window.location.search || "");
    const initialQuery = (urlParams.get("q") || "").trim();
    const initialSearchType = (urlParams.get("search_type") || "keyword").trim();
    const initialSource = (urlParams.get("source") || "ALL").trim();

    function renderNews(items) {
        newsList.empty();
        if (!items || items.length === 0) {
            newsList.append('<article class="news-card"><h3>暂无匹配资讯</h3><p>请调整来源、关键词或搜索方式后重试。</p></article>');
            return;
        }
        items.forEach((item) => {
            const title = item.link
                ? `<a href="${item.link}" target="_blank" rel="noopener noreferrer">${item.title}</a>`
                : item.title;
            const publishedAt = item.published_at || "--";
            const html = `
                <article class="news-card news-timeline-item">
                    <div class="news-time">${publishedAt}</div>
                    <h3>${title}</h3>
                    <div class="news-meta">${item.source || "未知来源"}</div>
                    <p>${item.summary}</p>
                </article>
            `;
            newsList.append(html);
        });
    }

    function loadSources() {
        $.get("/api/news/sources")
            .done(function (sources) {
                (sources || []).forEach((source) => {
                    sourceSelect.append(`<option value="${source}">${source}</option>`);
                });
                if (sourceSelect.find(`option[value="${initialSource}"]`).length > 0) {
                    sourceSelect.val(initialSource);
                } else {
                    sourceSelect.val("ALL");
                }
                loadNews();
            })
            .fail(function () {
                loadNews();
            });
    }

    function loadNews() {
        const selectedSearchType = searchTypeSelect.length ? (searchTypeSelect.val() || "keyword") : "keyword";
        const selectedQuery = queryInput.length ? (queryInput.val() || "").trim() : "";
        const params = {
            source: sourceSelect.val() || "ALL",
            search_type: selectedSearchType,
            q: selectedQuery,
            mode,
        };
        $.get("/api/news", params, function (items) {
            renderNews(items);
        });
    }

    if (searchBtn.length) {
        searchBtn.on("click", function () {
            loadNews();
        });
    }

    if (resetBtn.length) {
        resetBtn.on("click", function () {
            sourceSelect.val("ALL");
            if (searchTypeSelect.length) {
                searchTypeSelect.val("keyword");
            }
            if (queryInput.length) {
                queryInput.val("");
            }
            loadNews();
        });
    }

    if (queryInput.length) {
        queryInput.on("keydown", function (event) {
            if (event.key === "Enter") {
                event.preventDefault();
                loadNews();
            }
        });
    }

    sourceSelect.on("change", loadNews);
    if (searchTypeSelect.length) {
        searchTypeSelect.on("change", loadNews);
    }

    if (queryInput.length) {
        queryInput.val(initialQuery);
    }
    if (searchTypeSelect.length) {
        if (searchTypeSelect.find(`option[value="${initialSearchType}"]`).length > 0) {
            searchTypeSelect.val(initialSearchType);
        } else {
            searchTypeSelect.val("keyword");
        }
    }
    loadSources();
});
