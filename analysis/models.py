from ckeditor.fields import RichTextField
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import User
from django.db import models

from django.db.models.signals import m2m_changed
from django_extensions.db.fields import AutoSlugField

from chemical.models import Chemical
from genome.models import Gene, GenePack

from django.dispatch import receiver
from genericm2m.models import RelatedObjectsDescriptor


class Symptom(models.Model):
    name = models.CharField(max_length=255)
    slug = AutoSlugField(populate_from="name", max_length=255)
    selfhacked_link = models.CharField(max_length=255, blank=True)
    related_objects = RelatedObjectsDescriptor()

    def __str__(self):
        return self.name


class SystemSymptoms(models.Model):
    system = models.ForeignKey("System", on_delete=models.CASCADE, null=False)
    symptom = models.ForeignKey("Symptom", on_delete=models.CASCADE, null=False)
    weight = models.FloatField(default=0.0, null=False, blank=False)

    def __str__(self):
        return "%s <%s> %s" % (self.system, self.weight, self.symptom,)

    class Meta:
        verbose_name = "System Symptom"
        verbose_name_plural = "System Symptoms"


class System(models.Model):
    name = models.CharField(max_length=255, blank=False, null=False)
    short_name = models.CharField(max_length=255, blank=True, null=True)
    slug = AutoSlugField(populate_from="name", max_length=255, blank=False, null=False)
    threshold = models.FloatField(default=0, null=False, blank=False)
    description = RichTextField(null=True, blank=True)
    threshold_description = RichTextField(null=True, blank=True)
    symptoms = models.ManyToManyField(Symptom, blank=False, through=SystemSymptoms)
    genes = models.ManyToManyField(Gene, blank=True)
    chemicals = models.ManyToManyField(Chemical, blank=True)
    gene_packs = models.ManyToManyField(GenePack, blank=True)
    user = models.ForeignKey(User, default=1, related_name='systems')

    def __str__(self):
        return self.name


class CustomUserSymptom(models.Model):
    symptom = models.CharField(max_length=255, null=False, blank=False, unique=True)
    user = models.ManyToManyField(User, related_name='custom_symptoms', through="CustomSymptomSeverity")

    def count_user(self):
        return self.user.count()

    def __str__(self):
        return self.symptom


class CustomSymptomSeverity(models.Model):
    customusersymptom = models.ForeignKey(CustomUserSymptom, related_name='custom_symptom_severity_through')
    user = models.ForeignKey(User, related_name='custom_symptom_severity_through')
    severity = models.IntegerField(default=0)

    class Meta:
        db_table = 'analysis_customusersymptom_user'


class CustomUserCondition(models.Model):
    condition = models.CharField(max_length=255, null=False, blank=False, unique=True)
    user = models.ManyToManyField(User, related_name='custom_conditions', through="CustomConditionSeverity")

    def __str__(self):
        return self.condition


class CustomConditionSeverity(models.Model):
    customusercondition = models.ForeignKey(CustomUserCondition, related_name='custom_condition_severity_through')
    user = models.ForeignKey(User, related_name='custom_condition_severity_through')
    severity = models.IntegerField(default=0)


@receiver(m2m_changed, sender=System.gene_packs.through)
def add_genes_from_gene_pack(instance, action, pk_set, **kwargs):
    if action == 'pre_remove':
        genes_to_remove = Gene.objects.filter(related_gene_pack__id__in=pk_set)
        instance.genes.remove(*list(genes_to_remove))
    if action == 'pre_add':
        genes_to_add = Gene.objects.filter(related_gene_pack__id__in=pk_set)
        instance.genes.add(*list(genes_to_add))
