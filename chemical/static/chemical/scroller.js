function scrollToPosition(elem) {
    $('html, body').animate({
        scrollTop: parseInt(elem.offset().top - $(".top-navbar").height() - 10)
    }, 1000);
}

var hash = window.location.hash;
if (hash) {
    var $this = $(hash);
    if ($this.length > 0) {
        var $icon = $this.find('.fa');
        $icon.hasClass('fa-plus');
        $icon.removeClass("fa-plus").addClass("fa-minus");
        $this.next().slideToggle();
        scrollToPosition($this);
    }
}

$('.panel-toggle .panel-heading').on('click', function () {
    var $this = $(this);
    var $icon = $this.find('.fa');
    if ($icon.hasClass('fa-plus')) {
        $icon.removeClass("fa-plus").addClass("fa-minus");
        window.location.hash = '#' + $this.attr('id');
        scrollToPosition($this);
    }
    else
        $icon.removeClass("fa-minus").addClass("fa-plus");
    $this.next().slideToggle();

    if(typeof Highcharts !== "undefined" && Highcharts.charts.length > 0)
        Highcharts.charts[0].reflow();

});