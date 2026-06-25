from django import forms
from django.contrib.auth.models import User
from django.conf import settings
from .models import Profile

class RegisterForm(forms.ModelForm):

    first_name = forms.CharField(
        label='First Name(s)',
        max_length=150
    )

    last_name = forms.CharField(
        label='Last Name',
        max_length=150
    )

    email = forms.EmailField()

    password = forms.CharField(
        widget=forms.PasswordInput
    )

    confirm_password = forms.CharField(
        widget=forms.PasswordInput
    )

    class Meta:
        model = User

        fields = [
            'first_name',
            'last_name',
            'email',
            'password'
        ]

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', 'Passwords do not match.')

        return cleaned_data

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        domain = email.split('@')[-1] if '@' in email else ''
        allowed_domains = getattr(settings, 'ORG_EMAIL_DOMAINS', ['strathmore.edu'])

        if domain not in allowed_domains:
            raise forms.ValidationError(
                f"Only organizational email addresses are allowed: {', '.join(allowed_domains)}."
            )

        if User.objects.filter(username__iexact=email).exists():
            raise forms.ValidationError('An account with this email already exists.')

        return email

    def save(self, commit=True):
        user = super().save(commit=False)

        # Use email as username so registration does not require a separate username field.
        user.username = self.cleaned_data['email'].lower()
        user.email = self.cleaned_data['email'].lower()
        user.set_password(self.cleaned_data['password'])

        if commit:
            user.save()
            Profile.objects.create(
                user=user,
                role='student'
            )

        return user


class StudentAttachmentDetailsForm(forms.ModelForm):
    first_name = forms.CharField(label='First Name', max_length=150)
    last_name = forms.CharField(label='Last Name', max_length=150)

    class Meta:
        model = Profile
        fields = [
            'school_id',
            'course',
            'year_of_study',
            'organization_name',
            'attachment_type',
        ]
        widgets = {
            'year_of_study': forms.NumberInput(attrs={'min': 1, 'max': 8}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        for name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'
            if name == 'attachment_type':
                field.widget.attrs['class'] = 'form-select'

        required_fields = [
            'school_id',
            'course',
            'year_of_study',
            'organization_name',
            'attachment_type',
        ]
        for field_name in required_fields:
            self.fields[field_name].required = True

        if self.user:
            self.fields['first_name'].initial = self.user.first_name
            self.fields['last_name'].initial = self.user.last_name

    def clean_year_of_study(self):
        year = self.cleaned_data.get('year_of_study')
        if year is None:
            return year

        if year < 1 or year > 8:
            raise forms.ValidationError('Year of study must be between 1 and 8.')

        return year

    def save(self, commit=True):
        profile = super().save(commit=False)

        if self.user is not None:
            self.user.first_name = self.cleaned_data['first_name'].strip()
            self.user.last_name = self.cleaned_data['last_name'].strip()
            if commit:
                self.user.save(update_fields=['first_name', 'last_name'])

        if commit:
            profile.save()

        return profile


class StudentOrganizationLocationForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = [
            'organization_location',
            'organization_main_road',
            'organization_latitude',
            'organization_longitude',
        ]
        widgets = {
            'organization_location': forms.TextInput(attrs={'class': 'form-control'}),
            'organization_main_road': forms.TextInput(attrs={'class': 'form-control'}),
            'organization_latitude': forms.HiddenInput(),
            'organization_longitude': forms.HiddenInput(),
        }

    def clean(self):
        cleaned_data = super().clean()
        location = (cleaned_data.get('organization_location') or '').strip()

        if not location:
            self.add_error('organization_location', 'Please select or enter the organization location.')

        return cleaned_data