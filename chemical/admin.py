from dal import autocomplete
from django.contrib import admin

# Register your models here.
from django.contrib.admin import widgets
from django.core.urlresolvers import reverse
from django.db import models
from django.utils.safestring import mark_safe
from mptt.admin import TreeRelatedFieldListFilter, DraggableMPTTAdmin

from chemical.forms import ChemicalGeneInteractionForm, ChemicalGeneInteractionActionForm, ChemicalForm, \
    ChemicalTargetMechanismForm, ChemicalPathway, ChemicalConcentrationAdminForm, ChemicalPathwayForm
from chemical.models import Chemical, Organism, ChemicalGeneInteractionType, ChemicalGeneInteraction, \
    ChemicalGeneInteractionAction, SubstanceCategory, HealthEffect, ChemicalMechanismOfAction, ChemicalT3DBData, \
    ChemicalTargetMechanism, Preparations, ChemicalConcentration
from genome.admin import FieldsLoggerMixin


class MyTreeRelatedFieldListFilter(TreeRelatedFieldListFilter):
    mptt_level_indent = 20
    rel_name = "categories"

    def __init__(self, field, request, params, model, model_admin, field_path):
        super(MyTreeRelatedFieldListFilter, self).__init__(field, request, params,
                                                         model, model_admin, field_path)
        self.lookup_kwarg = '%s__%s__inhierarchy' % (field_path, self.rel_name)


class ChemicalMechanismOfActionInline(admin.TabularInline):
    model = ChemicalTargetMechanism
    extra = 0
    readonly_fields = ("mechanism_of_action", "target", "reference")

    # formfield_overrides = {
    #     models.TextField: {'widget': widgets.AdminTextInputWidget()},
    # }


class ChemicalT3DBDataInline(admin.StackedInline):
    model = ChemicalT3DBData
    fields = ('description', 'metabolism', 'uses_sources', 'symptoms', 'treatment', 'route_of_exposure',)
    extra = 0
    # formfield_overrides = {
    #     models.TextField: {'widget': widgets.AdminTextInputWidget()},
    # }


@admin.register(Chemical)
class ChemicalAdmin(FieldsLoggerMixin):
    form = ChemicalForm
    list_display = ("name", "category_associated_from", "synonyms", "categories_list", "health_effects_list",
                    "recommendation_status", "view_page",)
    search_fields = ("name", "category_associated_from",)
    list_filter = (
        "merging_status", ("categories", MyTreeRelatedFieldListFilter,),
    )
    inlines = (ChemicalT3DBDataInline, ChemicalMechanismOfActionInline,)

    def get_queryset(self, request):
        query_set = super(ChemicalAdmin, self).get_queryset(request)
        return query_set.prefetch_related("categories", "health_effects")

    def view_page(self, inst):
        return mark_safe('<a href="%s" style="white-space: nowrap;">View Page</a>' % reverse("chemical:chemical", kwargs={"chemical": inst.slug}))

    def categories_list(self, obj):
        return ", ".join([item.name for item in obj.categories.all()])

    categories_list.short_description = "Categories"

    def health_effects_list(self, obj):
        return ", ".join([item.name for item in obj.health_effects.all()])

    health_effects_list.short_description = "Health Effects"


@admin.register(Organism)
class OrganismAdmin(admin.ModelAdmin):
    list_display = ("latin_name", "english_name",)
    search_fields = ("latin_name", "english_name",)
    prepopulated_fields = {"slug": ("latin_name",)}
    list_filter = ["food_group", "food_type"]


class ChemicalGeneInteractionActionInline(admin.TabularInline):
    model = ChemicalGeneInteractionAction
    extra = 0


@admin.register(ChemicalGeneInteractionType)
class ChemicalGeneInteractionTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "parent_code",)
    search_fields = ("name",)


@admin.register(ChemicalGeneInteraction)
class ChemicalGeneInteractionAdmin(admin.ModelAdmin):
    def actions_callable(self, inst):
        return ", ".join(["%s %s" % (o.action, o.interaction_type,) for o in inst.actions.all()])
    actions_callable.short_description = "Actions"

    form = ChemicalGeneInteractionForm
    list_display = ("gene", "chemical", "organism", "actions_callable",)
    search_fields = ("gene__name", "chemical__name", "organism__english_name")
    inlines = [ChemicalGeneInteractionActionInline, ]


@admin.register(SubstanceCategory)
class SubstanceCategoryAdmin(DraggableMPTTAdmin):
    mptt_level_indent = 20
    mptt_indent_field = "name"


@admin.register(HealthEffect)
class HealthEffectAdmin(admin.ModelAdmin):
    list_display = ("name", "description", "slug")
    search_fields = ("name",)


@admin.register(ChemicalPathway)
class ChemicalPathwayAdmin(admin.ModelAdmin):
    list_display = ("chemical", "pathway_name", "p_value",)
    search_fields = ("chemical",)
    form = ChemicalPathwayForm


@admin.register(Preparations)
class PreparationsAdmin(admin.ModelAdmin):
    list_display = ('name', "food_group", "food_subgroup")
    search_fields = ("name",)
    list_filter = ["food_group", "food_type"]


@admin.register(ChemicalConcentration)
class ChemicalConcentrationAdmin(admin.ModelAdmin):
    list_display = ("orig_compound_name", "conc", "conc_unit", "preparation", "organism",)
    search_fields = ("conc",)
    form = ChemicalConcentrationAdminForm

    def get_queryset(self, request):
        return super(ChemicalConcentrationAdmin, self).get_queryset(request).exclude(orig_compound_name='')
