function secondsToStr (delta) {
    "use strict";
    var hours, minutes, seconds;
    if ( !delta ) { return '00:00:00'; }
    delta = delta.toFixed(0);
    hours = Math.floor(delta / 3600);
    delta %= 3600;
    minutes = Math.floor(delta / 60);
    seconds = delta % 60;
    if ( seconds < 10 ) { seconds = '0' + seconds; }
    if ( minutes < 10 ) { minutes = '0' + minutes; }
    if ( hours < 10 ) { hours = '0' + hours; }
    return hours + ':' + minutes + ':' + seconds;
}

function isNumber(n) {
    "use strict";
    return !isNaN(parseFloat(n)) && isFinite(n);
}

function showFadeAlert(message, state, ms, $block) {
    "use strict";
    var $alert = showAlert(message, state, $block);
    ms = typeof ms !== 'undefined' ? ms : 5000;
    window.setTimeout(function() {
        $alert.fadeTo(500, 0).slideUp(500, function() { $(this).remove(); });
    }, ms);
}

function showAlert(message, state, $block) {
    "use strict";
    var $alert;
    $block = typeof $block !== 'undefined' ? $block : $('div.alert-block');
    $alert = $('<div class="alert alert-' + state + ' fade in"></div>')
        .append('<button class="close" data-dismiss="alert" type="button">×</button>')
        .append(message).alert();
    $block.prepend($alert);
    return $alert;
}

function selectErrorMessage(xhr) {
    "use strict";
    if (xhr.status < 500) {
        return 'An error occurred. Refresh page and try again, please.';
    } else {
        return 'Training service is unavailable, please try later.';
    }
}

function standardErrorHandler(xhr) {
    "use strict";
    showErrorAlert(selectErrorMessage(xhr));
}

function showInfoAlert(message) {
    "use strict";
    showAlert(message, 'success');
}

function showErrorAlert(message) {
    "use strict";
    showAlert(message, 'error');
}

function parseErrorResponse(xhr) {
    "use strict";
    var problem = JSON.parse(xhr.responseText).problem, message;
    if (typeof problem === 'string') {
        message = problem;
    } else if ('__all__' in problem) {
        message = problem.__all__[0];
    } else {
        message = JSON.stringify(problem);
    }
    return message;
}

function sumReduce(values) {
    "use strict";
    return _.reduce(values, function(memo, num) {
        return memo + num;
    }, 0);
}

function scrollToAnchor(aid){
    var aTag = $("a[name='"+ aid +"']");
    $('html, body').animate({scrollTop: aTag.offset().top}, 'slow');
}

function scrollToDataset() {
    var $datasetItem = $('.accordion-toggle').not('.collapsed'),
        datasetItemOffset = 0;
    if ($datasetItem.offset()) {
        datasetItemOffset = $datasetItem.offset().top;
        $('html, body').animate({scrollTop: datasetItemOffset}, 'slow');
    }
}

function flexboxHack() {
    /* This needs to force update any wizard container because of this bug:
       http://code.google.com/p/chromium/issues/detail?id=369869 */

   $('.wizard .panel').addClass('panel-fix');
    setTimeout(function() {
        $('.wizard .panel').removeClass('panel-fix');
    }, 0);
}


$(function() {
    "use strict";
    $('span.time-str').each(function() {
        $(this).html(secondsToStr(parseInt($(this).html(), 10)));
    });

    $('#beta_top').on('click', function() {
        scrollToAnchor('beta');
    });

    /* Bootstrap collapse behavior fix */
    $('#predict-list').on('show', function (e) {
        var $id = $(e.target).prop('id');
        $('.accordion-toggle').addClass('collapsed');
        $('.accordion-toggle[href="#' + $id + '"]').removeClass('collapsed');
    });
});
