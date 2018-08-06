from django.contrib import admin
from .models import TraitMatches, SnpMatches
from .forms import SnpMatchesAdminForm


class SnpMatchesInline(admin.StackedInline):
    form = SnpMatchesAdminForm
    model = SnpMatches
    extra = 0


@admin.register(TraitMatches)
class TraitMatchesAdmin(admin.ModelAdmin):
    list_display = ('name', 'count', 'score', 'p_term', 'file')
    search_fields = ('name', 'p_term')
    list_filter = ('p_term',)
    inlines = (SnpMatchesInline,)


@admin.register(SnpMatches)
class SnpMatchesAdmin(admin.ModelAdmin):
    list_display = ('trait', 'user_snp', 'risk_allele', 'm_type', 'c_type')
    search_fields = ('user_snp__rsid',)
    list_filter = ('risk_allele', 'm_type', 'c_type')
