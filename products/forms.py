from django import forms
from .models import ProductReview
from django.core.exceptions import ValidationError

class ReviewForm(forms.ModelForm):
    class Meta:
        model = ProductReview
        fields = ['stars', 'content']
        widgets = {
            "stars": forms.NumberInput(attrs={
                "class": "form-control",
                "min": 1,
                "max": 5,
                "placeholder": "Rating (1-5 stars)"
            }),
            "content": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": "Write your review here..."
            }),
        }

    def clean_stars(self):
        stars = self.cleaned_data.get('stars')
        if stars < 1 or stars > 5:
            raise ValidationError("Rating must be between 1 and 5 stars.")
        return stars

    def clean_content(self):
        content = self.cleaned_data.get('content')
        if len(content.strip()) < 10:
            raise ValidationError("Review content must be at least 10 characters long.")
        return content
