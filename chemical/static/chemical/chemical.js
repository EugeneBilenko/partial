(function () {
    var interacts_gene_next_page = 1;
    var problematic_gene_next_page = 2;
    var disease_interaction_next_page = 2;

    $("#interacts-gene-load-more").click(function () {
        var $this= $(this);
        var query = $this.data('url') + '?page=' + interacts_gene_next_page;
        $(this).text('Loading...').attr("disabled", 'disabled');
        $.ajax({
            url: query,
            success: function (page) {
                $("#interacts-gene-load-more").text('Load more').removeAttr("disabled");
                paginator = page.paginator;
                if (!paginator.has_next) {
                    $('#interacts-gene-load-more').remove();
                }
                interacts_gene_next_page = paginator.next_page_number;

                var $table = $('#interacts-gene-table');
                if(page.data.trim()) {
                    $table.append(page.data);
                    $table.parents("table").show();
                } else {
                    $table.parents("table").replaceWith('<p>' + app.config.AJAX_NOINFO_MESSAGE + '</p>');
                }
            }
        }).always(function () {
            $('[data-toggle="tooltip"]').tooltip()
        });
    });

    $("#problematic-gene-load-more").click(function () {
        var $this= $(this);
        var query = $this.data('url') + '?page=' + problematic_gene_next_page + "&page_type=problematic-gene";
        $(this).text('Loading...').attr("disabled", 'disabled');
        $.ajax({
            url: query,
            success: function (page) {
                $("#problematic-gene-load-more").text('Load more').removeAttr("disabled");
                paginator = page.paginator;
                if (!paginator.has_next) {
                    $('#problematic-gene-load-more').remove();
                }
                problematic_gene_next_page = paginator.next_page_number;
                $.each(page.object_list, function (index, item) {
                    var row = '<tr>\
                            <td>\
                                <div class="modal-button" data-toggle="tooltip" title="' + item.summary + '">\
                                    <a href="/gene/' + item.slug + '/">' + item.gene.toUpperCase() + '</a>\
                                </div>\
                            </td>\
                            <td>\
                                <span>' + item.interaction + '</span>\
                            </td>\
                        </tr>';


                    $('#problematic-gene-table').append(row);
                });
            }
        }).always(function () {
            $('[data-toggle="tooltip"]').tooltip()
        });
    });

    $("#disease-interaction-load-more").click(function () {
        var $this= $(this);
        var query = $this.data('url') + '/?page=' + disease_interaction_next_page;
        $(this).text('Loading...').attr("disabled", 'disabled');
        $.ajax({
            url: query,
            success: function (page) {
                $("#disease-interaction-load-more").text('Load more').removeAttr("disabled");
                var paginator = page.paginator;
                if (!paginator.has_next) {
                    $('#disease-interaction-load-more').remove();
                }
                disease_interaction_next_page = paginator.next_page_number;
                $('#disease-interaction-table').append(page.data);
            }
        }).always(function () {
            $('[data-toggle="tooltip"]').tooltip()
        });
    });

    $('[data-toggle="tooltip"]').tooltip({container: 'body'})
    subscribe_tooltip();

})();
