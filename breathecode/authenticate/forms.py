from django.contrib.auth.models import User
from django.contrib.auth.forms import PasswordChangeForm
from django.forms.widgets import PasswordInput
from django import forms

class PickPasswordForm(forms.Form):
    token= forms.CharField(widget=forms.HiddenInput())
    callback= forms.CharField(required=False,widget=forms.HiddenInput())
    password1 = forms.CharField(
        min_length=8,
        widget=forms.PasswordInput(attrs={
            "type":"password",
            "label": "hello",
            "class":"form-control",
        }),
    )
    password2 = forms.CharField(
        min_length=10,
        widget=forms.PasswordInput(attrs={
                "type":"password",
                "class":"form-control",
            }))
    def __init__(self, params, *args, **kwargs):
        super(forms.Form, self).__init__(params,*args, **kwargs)
        self.fields['token'].widget.attrs.update({'initial': params.get('token')})
        self.fields['callback'].widget.attrs.update({'initial': params.get('callback')})
        
class PasswordChangeCustomForm(PasswordChangeForm):
    def __init__(self, user, *args, **kwargs):
        super(PasswordChangeCustomForm, self).__init__(user,*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs['class'] = 'form-control'