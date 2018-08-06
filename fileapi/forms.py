from dal import autocomplete
from django import forms

from genome.models import File


class FileFormAdmin(forms.ModelForm):
    class Meta:
        model = File
        fields = '__all__'
        widgets = {
            "user": autocomplete.ModelSelect2(url="genome_user_autocomplete"),
            "genes_to_look_at": autocomplete.ModelSelect2Multiple(url="genome_gene_autocomplete"),
        }
