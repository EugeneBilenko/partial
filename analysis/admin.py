from django.contrib import admin

# Register your models here.
from django.contrib.admin import TabularInline
from django.contrib.contenttypes.admin import GenericTabularInline
from django.core.urlresolvers import reverse
from django.utils.safestring import mark_safe
from django.db import models

from analysis.forms import SystemAdminForm, SymptomAdminInlineForm, ForeignObjectForm
from analysis.models import Symptom, System, SystemSymptoms, CustomSymptomSeverity, CustomConditionSeverity, \
    CustomUserCondition
from analysis.models import CustomUserSymptom


class SymptomAdminInline(admin.TabularInline):
    model = SystemSymptoms
    form = SymptomAdminInlineForm
    extra = 0


@admin.register(Symptom)
class SymptomAdmin(admin.ModelAdmin):
    form = ForeignObjectForm
    list_display = ("id", "slug", "name",)
    list_display_links = ("id", "slug",)
    search_fields = ("name", "slug",)
    readonly_fields = ("slug",)


@admin.register(System)
class SystemAdmin(admin.ModelAdmin):
    form = SystemAdminForm
    list_display = ("id", "slug", "name", "threshold", "symptoms_callable",)
    list_display_links = ("id", "slug",)
    search_fields = ("name", "slug",)
    readonly_fields = ("slug",)

    inlines = (SymptomAdminInline,)

    def symptoms_callable(self, inst):
        return mark_safe(", ".join(
            [('<a href="%s">%s</a>' % (reverse("admin:analysis_symptom_change", args=(o.pk,)), o.name,)) for o in inst.symptoms.all()]
        ))

    symptoms_callable.short_description = "Symptoms"


class CustomSymptomSeverityInline(TabularInline):
    model = CustomSymptomSeverity

    readonly_fields = ("user", "severity")
    fields = ("user", "severity")
    extra = 0

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(CustomUserSymptom)
class CustomUserSymptomAdmin(admin.ModelAdmin):
    search_fields = ['symptom']
    list_display = ('symptom', 'users')
    inlines = (CustomSymptomSeverityInline,)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(models.Count('user'))

    def users(self, instance):
        return instance.user__count

    users.admin_order_field = 'user__count'


class CustomConditionSeverityInline(TabularInline):
    model = CustomConditionSeverity

    readonly_fields = ("user", "severity")
    fields = ("user", "severity")
    extra = 0

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(CustomUserCondition)
class CustomUserConditionAdmin(admin.ModelAdmin):
    search_fields = ['condition']
    list_display = ('condition', 'users')
    inlines = (CustomConditionSeverityInline,)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(models.Count('user'))

    def users(self, instance):
        return instance.user__count

    users.admin_order_field = 'user__count'
