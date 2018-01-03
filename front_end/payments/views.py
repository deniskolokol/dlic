import json
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from django.conf import settings
from django.core.mail import mail_admins
from django.http import HttpResponse
from payments.models import Customer, get_stripe, Charge
from payments.forms import AmountForm

stripe = get_stripe()


@login_required
def index(request):
    try:
        customer = Customer.objects.get(user=request.user)
    except Customer.DoesNotExist:
        customer = None
    return render(request, 'payments/index.html',
                  {'key': settings.STRIPE_PUBLIC_KEY,
                   'customer': customer,
                   'ratio': settings.MIN_USD_RATIO / 100.})


@login_required
def save_card(request):
    def create_card():
        try:
            scu = stripe.Customer.create(email=request.user.email,
                                         card=request.POST['stripeToken'])
        except stripe.CardError, e:
            return {'status': 'error', 'message': e.message}
        except stripe.StripeError, e:
            mail_admins('Stripe Error', e.message, fail_silently=True)
            return {'status': 'error',
                    'message': 'Error occurred, try again later.'}
        Customer.objects.create(
            user=request.user,
            stripe_id=scu.id,
            card_exp_month=scu.active_card.exp_month,
            card_exp_year=scu.active_card.exp_year,
            card_last_4=scu.active_card.last4,
            card_fingerprint=scu.active_card.fingerprint,
            card_kind=scu.active_card.type
        )
        return {'status': 'success', 'message': 'Your credit card was saved.',
                'last_4': scu.active_card.last4,
                'exp_year': scu.active_card.exp_year,
                'exp_month': scu.active_card.exp_month}

    def update_card(customer):
        try:
            customer.update_card(request.POST['stripeToken'])
        except stripe.CardError, e:
            return {'status': 'error', 'message': e.message}
        except stripe.StripeError, e:
            mail_admins('Stripe Error', e.message, fail_silently=True)
            return {'status': 'error',
                    'message': 'Error occurred, try again later.'}
        return {'status': 'success',
                'message': 'Your credit card was updated.',
                'last_4': customer.card_last_4,
                'exp_year': customer.card_exp_year,
                'exp_month': customer.card_exp_month}
    try:
        customer = Customer.objects.get(user=request.user)
    except Customer.DoesNotExist:
        response = create_card()
    else:
        response = update_card(customer)
    return HttpResponse(json.dumps(response), content_type="application/json")


@login_required
def charge(request):
    customer = get_object_or_404(Customer, user=request.user)
    form = AmountForm(request.POST)
    if not form.is_valid():
        return HttpResponse(
            json.dumps({'status': 'error', 'message': form.errors}),
            content_type="application/json")
    amount = form.cleaned_data['amount']
    try:
        charge_ = stripe.Charge.create(customer=customer.stripe_id,
                                       amount=amount,
                                       currency='usd',
                                       description='Payment')
        Charge.objects.create(stripe_id=charge_.id,
                              customer=customer,
                              amount=amount)
        message = 'Thanks, you payed %s$!' % (amount / 100., )
        response = {'status': 'success', 'message': message}
    except stripe.StripeError, e:
        response = {'message': 'Error occurred, try again later.',
                    'status': 'error'}
        mail_admins('Stripe Error',
                    e.message + '\nUser: ' + str(request.user),
                    fail_silently=True)
    return HttpResponse(json.dumps(response), content_type="application/json")
