from django.contrib.auth.forms import PasswordChangeForm
from django import forms


class SyncGithubUsersForm(forms.Form):
    html = forms.CharField(
        widget=forms.Textarea(attrs={"name": "html", "rows": "5", "cols": "5", "class": "form-control"})
    )


class ResetPasswordForm(forms.Form):
    callback = forms.CharField(required=False, widget=forms.HiddenInput())
    email = forms.EmailField(
        widget=forms.EmailInput(
            attrs={
                "label": "email",
                "class": "form-control",
            }
        ),
    )

    def __init__(self, params, *args, **kwargs):
        super(forms.Form, self).__init__(params, *args, **kwargs)
        self.fields["callback"].widget.attrs.update({"initial": params.get("callback")})

        self.meta = {
            "heading": "Forgot password",
            "intro": "Fill out your email and we will send a password reset link if we find your email in our database.",
            "btn_label": "Get password reset link",
        }


class LoginForm(forms.Form):
    url = forms.CharField(required=False, widget=forms.HiddenInput())
    email = forms.EmailField(
        widget=forms.EmailInput(
            attrs={
                "label": "email",
                "class": "form-control",
            }
        ),
    )
    password = forms.CharField(
        min_length=8,
        widget=forms.PasswordInput(
            attrs={
                "type": "password",
                "class": "form-control",
            }
        ),
    )

    def __init__(self, params, *args, **kwargs):
        super(forms.Form, self).__init__(params, *args, **kwargs)
        self.fields["url"].widget.attrs.update({"initial": params.get("url")})


class PickPasswordForm(forms.Form):
    token = forms.CharField(widget=forms.HiddenInput())
    callback = forms.CharField(required=False, widget=forms.HiddenInput())
    password1 = forms.CharField(
        min_length=8,
        label="New password",
        widget=forms.PasswordInput(
            attrs={
                "type": "password",
                "class": "form-control",
            }
        ),
    )
    password2 = forms.CharField(
        min_length=8,
        label="Repeat your new password",
        widget=forms.PasswordInput(
            attrs={
                "type": "password",
                "class": "form-control",
            }
        ),
    )

    def __init__(self, params, *args, **kwargs):
        super(forms.Form, self).__init__(params, *args, **kwargs)
        self.fields["token"].widget.attrs.update({"initial": params.get("token")})
        self.fields["callback"].widget.attrs.update({"initial": params.get("callback")})

        self.meta = {
            "heading": "Choose a password for your account",
            "intro": "Fill out both of the password fields with the same value",
            "btn_label": "Set my password",
        }


class InviteForm(forms.Form):
    token = forms.CharField(widget=forms.HiddenInput())
    callback = forms.CharField(required=False, widget=forms.HiddenInput())
    first_name = forms.CharField(
        min_length=2,
        widget=forms.TextInput(
            attrs={
                "type": "text",
                "label": "first_name",
                "class": "form-control",
            }
        ),
    )
    last_name = forms.CharField(
        min_length=2,
        widget=forms.TextInput(
            attrs={
                "type": "text",
                "label": "last_name",
                "class": "form-control",
            }
        ),
    )
    phone = forms.CharField(
        min_length=8,
        widget=forms.TextInput(
            attrs={
                "type": "text",
                "label": "phone",
                "class": "form-control",
            }
        ),
    )
    password = forms.CharField(
        min_length=8,
        widget=forms.PasswordInput(
            attrs={
                "type": "password",
                "label": "hello",
                "class": "form-control",
            }
        ),
    )
    repeat_password = forms.CharField(
        min_length=8,
        widget=forms.PasswordInput(
            attrs={
                "type": "password",
                "class": "form-control",
            }
        ),
    )

    def __init__(self, params, *args, **kwargs):
        super(forms.Form, self).__init__(params, *args, **kwargs)

        token = params["token"]
        if len(params["token"]) > 0:
            token = params["token"][0]
        callback = params["callback"]
        if len(params["callback"]) > 0:
            callback = params["callback"][0]

        self.fields["token"].widget.attrs.update({"initial": token})
        self.fields["callback"].widget.attrs.update({"initial": callback})


class PasswordChangeCustomForm(PasswordChangeForm):

    def __init__(self, user, *args, **kwargs):
        super(PasswordChangeCustomForm, self).__init__(user, *args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs["class"] = "form-control"
