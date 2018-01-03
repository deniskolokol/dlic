$(function() {
    "use strict";
    $('.main :header').each(function() {
        var x = parseInt(this.tagName.split('')[1], 10) - 2;
        x = (x > 0) ? x * 20 : 0;
        $('.refer').append('<li style="margin-left: ' + x + 'px;"><a href="#' + this.id + '">'  + $(this).html() + '</a></li>');
    });

    $('.oglav li a').click(function(e) {
        e.preventDefault();
        var href=$(this).attr('href');
        $('html, body').animate({
            scrollTop: $(href).offset().top - 50
        }, 200);
    });
});
