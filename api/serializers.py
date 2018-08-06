from django.core.urlresolvers import reverse
from rest_framework.fields import SerializerMethodField
from rest_framework.serializers import ModelSerializer, Serializer
from rest_framework import serializers

from analysis.models import CustomSymptomSeverity, CustomConditionSeverity
from chemical.models import ChemicalPathway, ChemicalGeneInteraction, Organism, ChemicalGeneInteractionAction, \
    ChemicalGeneInteractionType, ChemicalConcentration
from genome.models import Gene, UserProfileSymptoms, UserProfileCondition, UserProfile
from users.models import CollectedEmail
from genome.templatetags.genome_tags import genotype_frequency
from genome.templatetags import genome_tags


class ChemicalPathwaySerializer(ModelSerializer):
    details_page_url = SerializerMethodField()

    def get_details_page_url(self, instance):
        return reverse('pathway_details', args=(instance.pathway_id,))

    class Meta:
        model = ChemicalPathway
        fields = ('pathway_id', 'pathway_name', 'details_page_url',)


class OrganismSerializer(ModelSerializer):
    name = SerializerMethodField()

    def get_name(self, instance):
        return (instance.english_name if instance.english_name else instance.latin_name).title()

    class Meta:
        model = Organism
        fields = ('id', 'name',)


class GeneSerializer(ModelSerializer):
    name = SerializerMethodField()
    bad_gene = SerializerMethodField()
    contains_risk_allele = SerializerMethodField()
    details_page_url = SerializerMethodField()
    description = SerializerMethodField()

    def get_name(self, instance):
        return instance.name.upper()

    def get_bad_gene(self, instance):
        return getattr(instance, 'bad_gene', None)

    def get_contains_risk_allele(self, instance):
        return getattr(instance, 'contains_risk_allele', None)

    def get_details_page_url(self, instance):
        return reverse('gene', args=(instance.slug,))

    def get_description(self, instance):
        return instance.display_description

    class Meta:
        model = Gene
        fields = ('id', 'name', 'slug', 'description', 'description_simple', 'function', 'bad_gene', 'contains_risk_allele', 'details_page_url',)


class ChemicalGeneInteractionTypeSerializer(ModelSerializer):
    class Meta:
        model = ChemicalGeneInteractionType
        fields = ('id', 'name',)


class ChemicalGeneInteractionActionSerializer(ModelSerializer):
    interaction_type = SerializerMethodField()

    def get_interaction_type(self, instance):
        return ChemicalGeneInteractionTypeSerializer(instance.interaction_type).data

    class Meta:
        model = ChemicalGeneInteractionAction
        fields = ('id', 'action', 'interaction_type',)


class ChemicalGeneInteractionSerializer(ModelSerializer):
    gene = SerializerMethodField()
    organism = SerializerMethodField()
    actions = SerializerMethodField()
    pubmed_urls = SerializerMethodField()

    def get_gene(self, instance):
        return GeneSerializer(instance.gene).data

    def get_organism(self, instance):
        return OrganismSerializer(instance.organism).data

    def get_actions(self, instance):
        return ChemicalGeneInteractionActionSerializer(instance.actions, many=True).data

    def get_pubmed_urls(self, instance):
        return instance.pub_med_ids_as_list()

    class Meta:
        model = ChemicalGeneInteraction
        fields = ('id', 'pubmed_urls', 'gene', 'organism', 'actions',)


class ChemicalOrganismSerializer(Serializer):
    def create(self, validated_data):
        pass

    def update(self, instance, validated_data):
        pass

    name = serializers.CharField(max_length=250)
    organism__latin_name = serializers.CharField(max_length=250)
    organism__slug = serializers.CharField(max_length=250)
    conc_unit = serializers.CharField(max_length=250)
    max_conc = serializers.FloatField()
    conc_min = serializers.FloatField()
    conc_max = serializers.FloatField()
    details_page_url = SerializerMethodField()

    def get_details_page_url(self, instance):
        return reverse('chemical:organism', args=(instance.get("organism__slug"),))


class ChemicalPreparationSerializer(Serializer):
    def create(self, validated_data):
        pass

    def update(self, instance, validated_data):
        pass

    preparation__name = serializers.CharField(max_length=250)
    conc_unit = serializers.CharField(max_length=250)
    max_conc = serializers.FloatField()


class SnpSerializer(Serializer):
    rsid = serializers.CharField(max_length=250)
    id = serializers.IntegerField()
    genotype = serializers.CharField(max_length=250)
    frequency = SerializerMethodField()
    diseasetraits = SerializerMethodField()
    risk_alleles = SerializerMethodField()
    importance = serializers.CharField(max_length=250)
    genotype_html = SerializerMethodField()

    def get_genotype_html(self, instance):
        return genome_tags.genotype_badge(instance.genotype, instance.minor_allele, instance.genotype)

    def get_frequency(self, instance):
        return genotype_frequency(instance.genotype, instance.id)

    def get_risk_alleles(self, instance):
        return ', '.join(i for i in instance.risk_alleles if i)

    def get_diseasetraits(self, instance):
        return [{'name': d.get('f1'), 'slug': d.get('f2')} for d in instance.disease if d.get('f1')]


class UserProfileSymptomSerializer(ModelSerializer):

    class Meta:
        model = UserProfileSymptoms
        fields = '__all__'


class UserProfileConditionSerializer(ModelSerializer):

    class Meta:
        model = UserProfileCondition
        fields = '__all__'


class CustomSymptomSeveritySerializer(ModelSerializer):

    class Meta:
        model = CustomSymptomSeverity
        fields = '__all__'


class CustomConditionSeveritySerializer(ModelSerializer):

    class Meta:
        model = CustomConditionSeverity
        fields = '__all__'


class UserProfileSerializer(ModelSerializer):

    class Meta:
        model = UserProfile
        fields = '__all__'
