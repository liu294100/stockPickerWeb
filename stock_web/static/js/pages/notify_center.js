$(document).ready(function () {
    $("#send-notify").click(function () {
        const channels = [];
        $(".notify-channel:checked").each(function () {
            channels.push($(this).val());
        });

        $.ajax({
            url: "/api/notify/test",
            type: "POST",
            contentType: "application/json",
            data: JSON.stringify({
                message: $("#notify-message").val(),
                channels: channels,
            }),
            success: function (data) {
                $("#notify-result").text(JSON.stringify(data, null, 2));
            },
            error: function (xhr) {
                $("#notify-result").text(xhr.responseText);
            },
        });
    });
});
