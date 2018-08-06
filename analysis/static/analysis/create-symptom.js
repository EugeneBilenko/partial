/**
 * Created by developer on 2/21/17.
 */

$('select.genes').ajaxChosen({
        dataType: 'json',
        type: 'GET',
        url:'/genes-list-api/',
    }, {
            processItems: function(data){ return data.results; },
            useAjax: true,
            generateUrl: function(q){ return '/genes-list-api/' },
            minLength: 2
    }, {
        disable_search_threshold: 10,
        width: "100%"
});

$('select.chemicals').ajaxChosen({
        dataType: 'json',
        type: 'GET',
        url:'/chemicals-list-api/',
    }, {
            processItems: function(data){ return data.results; },
            useAjax: true,
            generateUrl: function(q){ return '/chemicals-list-api/' },
            minLength: 2
    }, {
        width: "100%",
});

$("select.symptoms").chosen({disable_search_threshold: 10, width: "50%"});

// $('select.symptoms').ajaxChosen({
//         dataType: 'json',
//         type: 'GET',
//         url:'/symptoms-list-api/',
//     }, {
//             processItems: function(data){ return data.results; },
//             useAjax: true,
//             generateUrl: function(q){ return '/symptoms-list-api/' },
//             minLength: 1
//     }, {
//         width: "100%",
// });

$(document).ready(function () {
    $('a.add-symptom-btn').on('click', function (event) {
        event.preventDefault();
        var row = $('#symptom-row').html();
        $('.symptom-table tbody').append(row);
        $("select.symptoms").chosen({disable_search_threshold: 10, width: "50%"});
    })

    $('table').on('click', '.delete-btn', function () {
        $(this).closest('tr').remove();
    })
});