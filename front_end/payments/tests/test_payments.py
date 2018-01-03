"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from django.test import TestCase
from payments.models import Charge, Customer
from django.contrib.auth import get_user_model
from django.conf import settings


ApiUser = get_user_model()


def create_customer(user, stripe_id='test_stripe_id', card_exp_month=1,
                    card_exp_year=2017, card_last_4=1234,
                    card_fingerprint='test_fingerprint', card_kind='visa'):
    return Customer.objects.create(
        user=user,
        stripe_id=stripe_id,
        card_exp_month=card_exp_month,
        card_exp_year=card_exp_year,
        card_last_4=card_last_4,
        card_fingerprint=card_fingerprint,
        card_kind=card_kind
    )


class ChargeTest(TestCase):
    def setUp(self):
        user = ApiUser.objects.create_user(email='test@example.org',
                                           password='123456')
        self.user = ApiUser.objects.get(pk=user.pk)

    def test_signup_gift(self):
        self.assertEqual(self.user.seconds_paid, 10800)

    def test_payment(self):
        customer = create_customer(user=self.user)
        charge = Charge.objects.create(customer=customer,
                                       stripe_id='test_stripe_id',
                                       amount=settings.MIN_USD_RATIO * 2)
        user = ApiUser.objects.get(pk=self.user.pk)
        self.assertEqual(charge.minutes, 2)
        self.assertEqual(user.seconds_paid, 182 * 60)

    def test_bulk_discount(self):
        customer = create_customer(user=self.user)
        # $205 = 550 min
        charge = Charge.objects.create(customer=customer,
                                       stripe_id='test_stripe_id',
                                       amount=20500)
        user = ApiUser.objects.get(pk=self.user.pk)
        self.assertEqual(charge.minutes, 550)
        self.assertEqual(user.seconds_paid, (550 + 180) * 60)
        # $500.20 = 1464 min
        charge = Charge.objects.create(customer=customer,
                                       stripe_id='test_stripe_id2',
                                       amount=50020)
        user = ApiUser.objects.get(pk=self.user.pk)
        self.assertEqual(charge.minutes, 1464)
        self.assertEqual(user.seconds_paid, (1464 + 550 + 180) * 60)
        # $1047.55 = 3321 min
        charge = Charge.objects.create(customer=customer,
                                       stripe_id='test_stripe_id3',
                                       amount=104755)
        user = ApiUser.objects.get(pk=self.user.pk)
        self.assertEqual(charge.minutes, 3321)
        self.assertEqual(user.seconds_paid, (3321 + 1464 + 550 + 180) * 60)

    def test_errors(self):
        customer = create_customer(user=self.user)
        charge = Charge.objects.create(customer=customer,
                                       stripe_id='test_stripe_id',
                                       amount=settings.MIN_USD_RATIO * 2)
        charge.minutes = 100
        with self.assertRaises(NotImplementedError):
            charge.save()

        with self.assertRaises(ValueError):
            charge = Charge.objects.create(customer=customer,
                                           stripe_id='test_stripe_id',
                                           amount=settings.MIN_USD_RATIO * 2.)
        with self.assertRaises(ValueError):
            charge = Charge.objects.create(customer=customer,
                                           stripe_id='test_stripe_id',
                                           amount=settings.MIN_USD_RATIO)
        with self.assertRaises(ValueError):
            charge = Charge.objects.create(
                customer=customer,
                stripe_id='test_stripe_id',
                amount=int(settings.MIN_USD_RATIO * 2.5)
            )
