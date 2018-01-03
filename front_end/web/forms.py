#coding: utf-8
from django import forms
from django.conf import settings
from web.models import ApiUser
from django.contrib.auth.forms import AuthenticationForm


class SigninForm(AuthenticationForm):
    def clean_username(self):
        username = self.cleaned_data['username'].lower()
        return username


class SignupForm(forms.Form):
    username = forms.EmailField(max_length=100)
    password = forms.CharField(min_length=5, widget=forms.PasswordInput)
    password_repeat = forms.CharField(min_length=5, widget=forms.PasswordInput)

    def clean_username(self):
        username = self.cleaned_data['username'].lower()
        return username

    def clean(self):
        cleaned_data = super(SignupForm, self).clean()
        if self.errors:
            return cleaned_data
        email = cleaned_data['username']
        password = cleaned_data['password']
        password_repeat = cleaned_data['password_repeat']
        if password != password_repeat:
            raise forms.ValidationError("Passwords don't match, please type them again.")
        if ApiUser.objects.filter(email=email).exists():
            raise forms.ValidationError("User with this name already exists")
        return cleaned_data
