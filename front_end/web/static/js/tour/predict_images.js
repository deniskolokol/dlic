$(document).ready(function() {
    window.myTour = jTour([
        {
            html: "This model has already been trained to recognize certain types of images. Go ahead and try uploading a few images that fall into these listed classes to see how the model performs. Before dragging the image, download it to your computer.<br><br>With Ersatz, you can train on any kind of vision dataset. See <a href='/help/data/#images'>here</a> to learn about using your own images.",
            element: 'div.dropbox',
            live: 15000,
            position: 'w'
        }
    ],{
        axis:'y',  // use only one axis prevent flickring on iOS devices
        animationIn: 'slideDown',
        animationOut: 'hide',
        easing: 'easeInOutExpo', //requires the jquery.easing plugin
        scrollDuration: 600,
        autostart: !getCookie('tourwasplayed-predict-images'),
        onStop: function(){
            //set the cookie with value 1 (true) and expire date in 365 days
            setCookie('tourwasplayed-predict-images', 1, 365);
        }
    });
});
