from django.contrib.auth.models import User
from django import forms
from .models import MENTORSHIP_STATUS


class CloseMentoringSessionForm(forms.Form):
    token = forms.CharField(widget=forms.HiddenInput())
    session_id = forms.CharField(widget=forms.HiddenInput())
    student_name = forms.CharField(widget=forms.TextInput(attrs={
        'class': 'form-control',
        'readonly': 'readonly',
    }))
    status = forms.CharField(label='Meeting status',
                             widget=forms.Select(choices=MENTORSHIP_STATUS, attrs={
                                 'class': 'form-control',
                             }))
    summary = forms.CharField(widget=forms.Textarea(attrs={'rows': 5, 'cols': 20, 'class': 'form-control'}))

    def __init__(self, params, *args, **kwargs):
        super(forms.Form, self).__init__(params, *args, **kwargs)
        self.fields['token'].widget.attrs.update({'initial': params.get('token')})
        self.fields['student_name'].widget.attrs.update({'initial': params.get('student_name')})
        self.fields['session_id'].widget.attrs.update({'initial': params.get('session_id')})
