
(function () {
    "use strict"

    // Pagination
    var $paged = $('.with-pagination');

    $paged.find('.pagination a').on('click', function (e) {
        $paged.find('.pagination li').removeClass('active');
        $paged.find('[data-page]').hide();
        var page = $(this).attr("href");
        $(this).parent().addClass("active");
        $paged.find('[data-page="' + page + '"]').show();
        return false;
    });
    $paged.find('.pagination a[href="#page-1"]').trigger('click');

    $('.remove-file-btn').on('click', function (e) {
        var $this = $(this);
        swal({
            title: "Are you sure?",
            text: "You will not be able to recover this file!",
            type: 'warning',
            confirmButtonText: "Yes, remove it.",
            showCancelButton: true,
            showConfirmButton: true,
            confirmButtonColor: "#D8482C"
        }).then(function () {
            $this.parent().find('form').trigger('submit');
        });
    });

    // "Use file" button

    var in_progress_ids = [];

    function get_files_data() {
        $.get("/fileapi/sse/", {files: in_progress_ids}, function (e) {
            var event = JSON.parse(e);
            var data = event.data;
            $.each(data, function () {
                var $progress = $("#progress-" + this.file_id);
                if(in_progress_ids.indexOf(this.file_id) == -1)
                    in_progress_ids.push(this.file_id);
                if(this.status == "processing") {
                    var $progressbar = $progress.find(".progress-bar");
                    if($progressbar.length == 0) {
                        var tpl = $('#tpl-file-progressbar').html();
                        tpl = tpl.replace('{value}', this.progress);
                        tpl = tpl.replace('{file_id}', this.file_id);
                        $progress.html(tpl);
                    }
                    $progressbar.css({
                        width: this.progress + "%"
                    });
                    $progressbar.find('span').text(this.progress + "%");
                } else {
                    if(this.status == "completed" || this.status == "error")
                        in_progress_ids = in_progress_ids.filter((function (v) {
                            return v != this.file_id;
                        }).bind(this));
                    if(this.status == "completed")
                        $progress.replaceWith('<td class="text-primary" id="progress-' + this.file_id + '">' + this.status_display + '</td>');
                    else if (this.status == "error")
                        $progress.replaceWith('<td class="text-danger" id="progress-' + this.file_id + '">' + this.status_display + '</td>');
                    else
                        $progress.replaceWith('<td class="text-muted" id="progress-' + this.file_id + '">' + this.status_display + '</td>');
                }
            });
            if(data.length > 0)
                setTimeout(get_files_data, 10000);
        });
    }
    get_files_data();
})();
