from django import forms


class DeliverAssigntmentForm(forms.Form):
    token = forms.CharField(widget=forms.HiddenInput())
    task_id = forms.CharField(widget=forms.HiddenInput())
    callback = forms.CharField(required=False, widget=forms.HiddenInput())
    task_name = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "readonly": "readonly",
            }
        )
    )
    github_url = forms.URLField(
        widget=forms.TextInput(
            attrs={
                "placeholder": "Please specify the github repository URL for this assignment.",
                "type": "url",
                "class": "form-control",
            }
        )
    )
    live_url = forms.URLField(
        required=False,
        widget=forms.TextInput(
            attrs={
                "placeholder": "Optionally you can also specify the live URL",
                "type": "url",
                "class": "form-control",
            }
        ),
    )

    def __init__(self, params, *args, **kwargs):
        super(forms.Form, self).__init__(params, *args, **kwargs)
        self.fields["token"].widget.attrs.update({"initial": params.get("token")})
        self.fields["callback"].widget.attrs.update({"initial": params.get("callback")})
        self.fields["task_name"].widget.attrs.update({"initial": params.get("task_name")})
        self.fields["task_id"].widget.attrs.update({"initial": params.get("task_id")})
