from django import forms
from django.conf import settings


class AmountForm(forms.Form):
    amount = forms.DecimalField(min_value=0.5, decimal_places=2)

    def clean_amount(self):
        amount = self.cleaned_data['amount']
        amount = int(amount * 100)
        if amount % settings.MIN_USD_RATIO != 0:
            raise forms.ValidationError('Not a integer number of minutes.')
        return amount
