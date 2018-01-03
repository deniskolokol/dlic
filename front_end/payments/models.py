import stripe
from django.db import models
from django.db.models import F
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model


ApiUser = get_user_model()
stripe.api_key = settings.STRIPE_SECRET_KEY
stripe.api_version = '2013-02-13'


def get_stripe():
    return stripe


class StripeObject(models.Model):

    stripe_id = models.CharField(max_length=50, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta(object):
        abstract = True


class Customer(StripeObject):

    user = models.OneToOneField(ApiUser, null=True)
    card_fingerprint = models.CharField(max_length=200, blank=True)
    card_last_4 = models.CharField(max_length=4, blank=True)
    card_kind = models.CharField(max_length=50, blank=True)
    card_exp_month = models.IntegerField()
    card_exp_year = models.IntegerField()

    def __unicode__(self):
        return unicode(self.user)

    @property
    def stripe_customer(self):
        return stripe.Customer.retrieve(self.stripe_id)

    def update_card(self, token):
        scu = self.stripe_customer
        scu.card = token
        scu.save()
        self.card_exp_month = scu.active_card.exp_month
        self.card_exp_year = scu.active_card.exp_year
        self.card_last_4 = scu.active_card.last4
        self.card_fingerprint = scu.active_card.fingerprint
        self.card_kind = scu.active_card.type
        self.save()


class Charge(StripeObject):

    customer = models.ForeignKey(Customer)
    amount = models.IntegerField()
    ratio = models.IntegerField(default=lambda: settings.MIN_USD_RATIO)
    discount = models.IntegerField(default=0)
    minutes = models.IntegerField()

    def save(self, *args, **kwargs):
        if self.pk:
            raise NotImplementedError('Changing charge is not allowed.')
        if not isinstance(self.amount, int):
            raise ValueError('Amount should be integer.')
        if self.amount < 50:
            raise ValueError('Stripe doesn\'t allow charges below 50 cents.')
        if self.amount % settings.MIN_USD_RATIO != 0:
            raise ValueError('Amount should be proportional to the %s'
                             % settings.MIN_USD_RATIO)
        discounts = sorted(settings.BULK_DISCOUNT,
                           key=lambda x: x[0], reverse=True)
        discount = next((x[1] for x in discounts if x[0] <= self.amount), 0)
        self.discount = (1 + discount / 100.)
        self.ratio = settings.MIN_USD_RATIO
        self.minutes = int(self.amount / self.ratio * self.discount)
        super(Charge, self).save(*args, **kwargs)

    def __unicode__(self):
        return (unicode(self.customer.user) +
                u':$' + unicode(self.amount / 100.))


class Gift(models.Model):
    user = models.ForeignKey(ApiUser, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    description = models.TextField(blank=True, null=True)
    minutes = models.IntegerField()

    def save(self, *args, **kwargs):
        if self.pk:
            raise NotImplementedError('Changing gifts is not allowed.')
        super(Gift, self).save(*args, **kwargs)

    def __unicode__(self):
        return unicode(self.user) + u':' + unicode(self.minutes) + u'min'


# signals
@receiver(post_save, sender=Charge)
def update_seconds_paid(sender, instance, created, **kwargs):
    if created:
        ApiUser.objects.filter(pk=instance.customer.user.pk).update(
            seconds_paid=F('seconds_paid') + instance.minutes * 60
        )


@receiver(post_save, sender=Gift)
def update_seconds_gifted(sender, instance, created, **kwargs):
    if created:
        ApiUser.objects.filter(pk=instance.user.pk).update(
            seconds_paid=F('seconds_paid') + instance.minutes * 60
        )


@receiver(post_save, sender=ApiUser)
def signup_gift(sender, instance, created, **kwargs):
    if created:
        Gift.objects.create(user=instance, minutes=settings.SIGNUP_MINUTES,
                            description='Sign up gift')
