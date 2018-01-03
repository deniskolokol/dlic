function initTour() {
    var tourOptions = [];
    if (location.pathname === '/dashboard/') {
        tourOptions = [{
            html: "<h1>Welcome to Ersatz</h1><hr>This short tour will guide you through the basics."
        }, {
            html: "To get help on any page, click here.",
            element: $('.nav.pull-right'),
            position: 'se'
        }, {
            html: "To use Ersatz, you need to start with data. This screen lets you see all of your data sources.",
            element: $('#df-list'),
            position: 'n'
        }, {
            html: 'We have provided the following datasets',
            element: $('#df-list'),
            position: 'n'
        }, {
            html: '"MNIST"',
            element: $('.dm-filename').filter(":contains('mnist')").first(),
            position: 'e'
        }, {
            html: '"IRIS"',
            element: $('.dm-filename').filter(":contains('iris')").first(),
            position: 'e'
        }, {
            html: "We have also taken the liberty of training sample models on these datasets.",
            element: $('a[href="/dashboard/ensembles/"]'),
            position: 's'
        }, {
            html: "If you'd like to upload your own data, you can do so by clicking here.",
            element: $('.upload-button'),
            position: 'e'
        }, {
            html: "Go wild or check out the docs for more information...",
            element: $('.docs-link'),
            position: 'se'
        }]
    } else if (location.pathname.indexOf('/data-wizard/') !== -1) {
        tourOptions = [{
            html: 'This is a wizard for preparing your data for use with Ersatz. Using this wizard, you can split your data, shuffle it, normalize it, and more.<br>Select the filters you would like to apply to this dataset and click "Finish" to create it'
        }]
    } else if (location.pathname.indexOf('/ensemble-wizard/') !== -1) {
        tourOptions = []
    }

    if (tourOptions.length) {
        if (!$('.start-page-tour').length) {
            $('.navbar ul.pull-right').append('<li><a class="start-page-tour" href="#"><i class="icon icon-white icon-play"></i> Tour</a></li>');
        } else {
            $('.start-page-tour').remove();
            $('.navbar ul.pull-right').append('<li><a class="start-page-tour" href="#"><i class="icon icon-white icon-play"></i> Tour</a></li>');
        }
    } else {
        $('.start-page-tour').remove();
    }

    var myTour = jTour(tourOptions, {
        axis:'y',
        animationIn: 'slideDown',
        animationOut: 'hide',
        easing: 'easeInOutExpo',
        scrollDuration: 600,
        autostart: !getCookie('tourwasplayed-dashboard-train'),
        onStop: function(){
            setCookie('tourwasplayed-dashboard-train', 1, 365);
        }
    });

    $('.start-page-tour').on('click', function(e) {
        e.preventDefault();
        myTour.start(0);
    });
};


function launchTour(message, cookieName) {
    var tourOptions = [{
            html: message
        }];

    var myTour = jTour(tourOptions, {
        axis:'y',
        animationIn: 'slideDown',
        animationOut: 'hide',
        easing: 'easeInOutExpo',
        scrollDuration: 600,
        autostart: !getCookie('tourwasplayed-' + cookieName),
        onStop: function(){
            setCookie('tourwasplayed-' + cookieName, 1, 365);
        }
    });

    myTour.start(0);
};

