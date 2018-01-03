"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from django.test import TestCase
from django.test.client import Client
from django.conf import settings
from django.core.urlresolvers import reverse
from web.models import ApiUser


class WebTest(TestCase):

    def test_signup_iframe_login(self):
        client = Client()
        response = client.get('/')
        self.assertEqual(response.status_code, 200)
        data = {
            "username": 'testiframe@example.com',
            'password': '123456',
            'password_repeat': '123456',
            'iframe': 'iframe',
        }
        response = client.post(reverse('register'), data=data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(reverse('sign_up'), response.request['PATH_INFO'])
        self.assertContains(response, 'Sign up completed successfully, please check your email')

    def test_register_login(self):
        client = Client()
        response = client.get('/')
        self.assertEqual(response.status_code, 200)
        data = {
            "username": 'test',
            'password': '123456',
            'password_repeat': '123456',
        }
        response = client.post(reverse('register'), data=data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(reverse('register'), response.request['PATH_INFO'])
        self.assertContains(response, 'Enter a valid email address.')
        data = {
            'username': 'test@example.com',
            'password': '123456',
        }
        response = client.post(reverse('register'),
                               data=data, follow=True)
        self.assertEqual(ApiUser.objects.all().count(), 0)
        self.assertContains(response, "This field is required.")
        data = {
            'username': 'test_password_repeat@example.com',
            'password': '123456',
            'password_repeat': '654321'
        }
        response = client.post(reverse('register'),
                               data=data, follow=True)
        self.assertEqual(ApiUser.objects.all().count(), 0)
        self.assertContains(response, "Passwords don&#39;t match, please type them again.")

        data = {
            'username': 'test@example.com',
            'password': '123456',
            'password_repeat': '123456',
        }
        response = client.post(reverse('register'), data=data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ApiUser.objects.all().count(), 1)
        self.assertEqual(ApiUser.objects.all()[0].seconds_paid, 10800)
        self.assertEqual(ApiUser.objects.all()[0].login_count, 1)
        assert reverse('dashboard_main') == response.request['PATH_INFO']
        self.assertEqual(len(ApiUser.objects.all()[0].apikey.key), 40)
        data = {'username': 'test@example.com', 'password': '123456'}
        response = client.post(reverse('login'), data=data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertRedirects(response, reverse('dashboard_main'))
        self.assertEqual(ApiUser.objects.all()[0].login_count, 2)
        self.assertEqual(ApiUser.objects.all()[0].seconds_paid, 10800)
        data = {'username': 'test@example.com', 'password': '123456wrong'}
        response = client.post(reverse('login'), data=data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(reverse('login'), response.request['PATH_INFO'])
        self.assertContains(response,
                            'Please enter a correct email '
                            'address and password.')
        self.assertEqual(ApiUser.objects.all()[0].login_count, 2)
        self.assertEqual(ApiUser.objects.all()[0].seconds_paid, 10800)

    def test_anonymous_access(self):
        client = Client()

        def test_access(url):
            response = client.get(reverse(url))
            self.assertEqual(response.status_code, 302)
            self.assertRedirects(response,
                                 reverse('home') + '?next=' + reverse(url))

        test_access('dashboard_admin')
        test_access('dashboard_credentials')
        test_access('help')
        test_access('dashboard_main')


class PageTest(TestCase):

    def setUp(self):
        self.client = Client()
        data = {
            'username': 'test@example.com',
            'password': '123456',
            'password_repeat': '123456',
        }
        response = self.client.post(reverse('register'),
                                    data=data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ApiUser.objects.all().count(), 1)
        self.user = ApiUser.objects.all()[0]
        data = {'username': 'test@example.com', 'password': '123456'}
        response = self.client.post(reverse('login'), data=data, follow=True)
        self.assertEqual(response.status_code, 200)

    def test_pages(self):
        #user's stats access
        response = self.client.get(reverse('dashboard_admin'), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertRedirects(response, reverse('dashboard_main'))
        self.assertNotContains(response, "User's stats")
        #api key
        response = self.client.get(reverse('dashboard_credentials'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.user.apikey.key)
        #help
        response = self.client.get(reverse('help_api_docs'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'APIv')
        #as admin
        self.user.is_superuser = True
        self.user.save()
        response = self.client.get(reverse('dashboard_admin'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "User's stats")
        response = self.client.get(reverse('dashboard_main'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "User's stats")
