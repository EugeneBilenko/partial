from dal import autocomplete
from django import forms

from .models import SnpMatches


class SnpMatchesAdminForm(forms.ModelForm):
    class Meta:
        model = SnpMatches
        fields = '__all__'
        widgets = {
            "study": autocomplete.ModelSelect2(url="genome_snp_study_autocomplete"),
            "rsid": autocomplete.ModelSelect2(url="genome_snp_autocomplete"),
        }
