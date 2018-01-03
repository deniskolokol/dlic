$(function() {
    "use strict";
    function recalcAmount() {
        var intRegex = /^\d+$/,
            num = $('#minutes').val(),
            ratio = parseFloat($('#ratio').val());
        if( intRegex.test(num) ) {
            $('.control-group').removeClass('error');
            $('input[name="amount"]').val(num * 41 / 100);
            $('#payButton').attr('disabled', false);
        } else {
            $('.control-group').addClass('error');
            $('input[name="amount"]').val('');
            $('#payButton').attr('disabled', true);
        }
    }

    $('#minutes').keyup(function() { recalcAmount(); })
                 .focusout(function() { recalcAmount(); })
                 .change(function() { recalcAmount(); });

    $('#payButton').click(function() {
        var csrf = $('input[name="csrfmiddlewaretoken"]').val(),
            amount = $('input[name="amount"]').val();
        $('.loader').show();
        $('.index').hide();
        $.post(
            '/payments/charge/',
            {amount: amount, csrfmiddlewaretoken: csrf},
            function(data) {
                $('.loader').hide();
                $('.index').show();
                showFadeAlert(JSON.stringify(data.message), data.status);
            },
            'json'
        );
    });

    $('#updateCardButton').click(function(){
        var key = $('input[name="key"]').val();
        var token = function(res){
            var csrf = $('input[name="csrfmiddlewaretoken"]').val();
            $('.loader').show();
            $('.index').hide();
            $.post(
                '/payments/save/',
                {stripeToken: res.id, csrfmiddlewaretoken: csrf},
                function(data) {
                    $('.loader').hide();
                    $('.index').show();
                    showFadeAlert(data.message, data.status);
                    if ( data.status === 'success' ) {
                        $('#exp_year').html(data.exp_year);
                        $('#exp_month').html(data.exp_month);
                        $('#last_4').html(data.last_4);
                        $('.no-card').hide();
                        $('.has-card').show();
                        $('.payment-form').show();
                        $('#updateCardButton').html('Update credit card');
                    }
                },
                'json'
            );
        };
        StripeCheckout.open({
            key:         key,
            description: 'Credit card information',
            panelLabel:  'Save',
            token:       token
        });
        return false;
    });
});
