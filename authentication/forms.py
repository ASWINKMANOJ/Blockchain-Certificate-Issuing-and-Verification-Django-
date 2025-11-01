from django import forms

class LoginForm(forms.Form):
    email = forms.EmailField(widget=forms.EmailInput(attrs={
        'class': 'form-control',
        'placeholder': 'Enter your email'
    }))
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-control',
        'placeholder': 'Enter your password'
    }))

class AuthorizeOrgForm(forms.Form):
    org_email = forms.EmailField(widget=forms.EmailInput(attrs={
        "class": "form-control",
        "placeholder": "Organization Email"
    }))

class IssueCertificateForm(forms.Form):
    certificate_id = forms.CharField(max_length=100)
    recipient_name = forms.CharField(max_length=200)
    course_name = forms.CharField(max_length=200)
