if (localStorage.getItem('job_id')){
    var report_file_status = localStorage.getItem('job_id').split(",");

    $.each(report_file_status, function(index, job_id) {
        doPoll(job_id);
    });
    
}

function doPoll(job_id){
    var url = '/fileapi/file-download-process/'+job_id+'/';
    
    $.get(url, function(data) {
        if (data.status != "complete"){
            setTimeout(function() {
                doPoll(job_id);
            }, 5000);
        } else{
            var $report_row = $("#"+data.report_type+"-"+data.genetic_report_id);
            $report_row.find('.file_status').text("Completed");
            var $file_url = $report_row.find('td.text-center div a.file_url').removeClass('disabled');
            var job_arr = localStorage.getItem('job_id').split(",");
            const index = job_arr.indexOf(data.genetic_report_id);
            job_arr.splice(index, 1);
            localStorage.setItem('job_id', job_arr);
        }
    });
}

var $cell = $('.card');

    //open and close card when clicked on card
    $cell.find('.js-expander').click(function() {

      var $thisCell = $(this).closest('.card');

      if ($thisCell.hasClass('is-collapsed')) {
        $cell.not($thisCell).removeClass('is-expanded').addClass('is-collapsed').addClass('is-inactive');
        $thisCell.removeClass('is-collapsed').addClass('is-expanded');
        
        if ($cell.not($thisCell).hasClass('is-inactive')) {
          //do nothing
        } else {
          $cell.not($thisCell).addClass('is-inactive');
        }

      } else {
        $thisCell.removeClass('is-expanded').addClass('is-collapsed');
        $cell.not($thisCell).removeClass('is-inactive');
      }
    });

    //close card when click on cross
    $cell.find('.js-collapser').click(function() {

      var $thisCell = $(this).closest('.card');

      $thisCell.removeClass('is-expanded').addClass('is-collapsed');
      $cell.not($thisCell).removeClass('is-inactive');

    });