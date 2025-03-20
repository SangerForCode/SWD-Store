from django import forms
from .models import *

class ItemForm(forms.ModelForm):
    class Meta:
        model = Item
        fields = ['name', 'description', 'price', 'category', 'hostel', 'phone']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'hostel': forms.Select(choices=[(hostel.name, hostel.name) for hostel in Hostel.objects.all()]),
            'category': forms.Select(choices=[(category.name, category.name) for category in Category.objects.all()]),
            'phone': forms.TextInput(attrs={'placeholder': '(WhatsApp) Required if not provided one before'})
        }
        labels = {
            'name': 'Product Name',
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        self.fields['hostel'].required = not self.user.hostel
        self.fields['phone'].required = not self.user.phone

    def clean(self):
        cleaned_data = super().clean()
        whatsapp_number = cleaned_data.get('phone')
        hostel = cleaned_data.get('hostel')

        if not self.user.phone and not whatsapp_number:
            self.add_error('phone', "WhatsApp number is required as you haven't provided one before.")

        if not self.user.hostel and not hostel:
            self.add_error('hostel', "Hostel is required as you haven't provided one before.")

        return cleaned_data

class FeedbackForm(forms.ModelForm):
    class Meta:
        model = Feedback
        fields = ['message']
        widgets = {
            'message': forms.Textarea(attrs={
                'rows': 5, 
                'placeholder': 'Share your thoughts, suggestions, or report any issues you encountered...'
            }),
        }