from django import forms
from .models import MENTORSHIP_STATUS


class CloseMentoringSessionForm(forms.Form):
    token = forms.CharField(widget=forms.HiddenInput())
    session_id = forms.CharField(widget=forms.HiddenInput())
    student_name = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "readonly": "readonly",
            }
        )
    )
    status = forms.CharField(
        label="Meeting status",
        widget=forms.Select(
            choices=MENTORSHIP_STATUS,
            attrs={
                "class": "form-control",
            },
        ),
    )
    summary = forms.CharField(widget=forms.Textarea(attrs={"rows": 5, "cols": 20, "class": "form-control"}))

    def __init__(self, params, *args, **kwargs):
        super(forms.Form, self).__init__(params, *args, **kwargs)
        self.fields["token"].widget.attrs.update({"initial": params.get("token")})

    def clean(self):
        super(CloseMentoringSessionForm, self).clean()
        status = self.cleaned_data.get("status")

        # if status == 'PENDING':
        #     raise ValidationError('You need to chose either Completed or Failed on the session status',
        #                           code='invalid')

        if status in ["PENDING", "STARTED"]:
            self._errors["status"] = self.error_class(
                ["You need to chose either Completed or Failed on the session status"]
            )

        return self.cleaned_data
