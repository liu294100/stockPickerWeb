$(document).ready(function () {
    const urlParams = new URLSearchParams(window.location.search);
    const code = urlParams.get("code");
    if (code) {
        $("#stock-code").val(code);
    }

    function showMessage(msg, type) {
        const alert = $("#trade-message");
        alert.removeClass("alert-success alert-danger").addClass(`alert-${type}`);
        alert.text(msg).show();
        setTimeout(() => alert.fadeOut(), 3000);
    }

    function loadAccountInfo() {
        $.get("/api/account", function (data) {
            const html = `
                <div>可用资金：${data.cash}</div>
                <div>持仓市值：${data.market_value}</div>
                <div>总资产：${data.total_assets}</div>
            `;
            $("#account-info").html(html);

            const tbody = $("#positions-table tbody");
            tbody.empty();
            if (data.positions && data.positions.length > 0) {
                data.positions.forEach((pos) => {
                    const profitClass = pos.profit >= 0 ? "text-success" : "text-danger";
                    const row = `
                        <tr>
                            <td>${pos.code}</td>
                            <td>${pos.name}</td>
                            <td>${pos.shares}</td>
                            <td>${pos.cost}</td>
                            <td>${pos.market_value}</td>
                            <td class="${profitClass}">${pos.profit}</td>
                            <td class="${profitClass}">${pos.profit_pct}%</td>
                        </tr>
                    `;
                    tbody.append(row);
                });
            } else {
                tbody.append('<tr><td colspan="7">暂无持仓</td></tr>');
            }
        });
    }

    function executeTrade(action) {
        const tradeCode = $("#stock-code").val();
        const quantity = $("#quantity").val();

        if (!tradeCode || !quantity) {
            showMessage("请填写完整信息", "danger");
            return;
        }

        $.ajax({
            url: `/api/trade/${action}`,
            type: "POST",
            contentType: "application/json",
            data: JSON.stringify({ code: tradeCode, quantity: parseInt(quantity, 10) }),
            success: function (response) {
                showMessage(response.message, "success");
                loadAccountInfo();
            },
            error: function (xhr) {
                const msg = xhr.responseJSON ? xhr.responseJSON.error : "交易失败";
                showMessage(msg, "danger");
            },
        });
    }

    loadAccountInfo();

    $("#btn-buy").click(function () {
        executeTrade("buy");
    });

    $("#btn-sell").click(function () {
        executeTrade("sell");
    });
});
