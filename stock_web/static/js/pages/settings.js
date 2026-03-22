$(document).ready(function () {
    $("#settings-form").submit(function (e) {
        e.preventDefault();
        const data = {};
        $(this)
            .serializeArray()
            .forEach((item) => {
                data[item.name] = item.value;
            });

        $.ajax({
            url: "/settings",
            type: "POST",
            contentType: "application/json",
            data: JSON.stringify(data),
            success: function () {
                alert("设置保存成功");
            },
            error: function () {
                alert("设置保存失败");
            },
        });
    });

    $("#test-notify").click(function () {
        $.ajax({
            url: "/api/notify/test",
            type: "POST",
            contentType: "application/json",
            data: JSON.stringify({ message: "This is a test notification from Stock Assistant Pro" }),
            success: function () {
                alert("测试消息已发送，请查看各渠道接收情况。");
            },
            error: function () {
                alert("测试消息发送失败");
            },
        });
    });
});
