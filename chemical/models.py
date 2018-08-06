from ckeditor.fields import RichTextField
from django.contrib.admin.models import LogEntry
from django.core.urlresolvers import reverse
from django.db import models
# Create your models here.
from mptt.fields import TreeForeignKey, TreeManyToManyField
from mptt.models import MPTTModel

from decodify.helpers import keeptags
from genome.mixins import ModelDiffMixin
from genome.models import Gene, DiseaseTrait, Pathway


class SubstanceCategory(MPTTModel):
    name = models.CharField(max_length=255, default=None)
    slug = models.SlugField(max_length=255, unique=True, default=None)
    parent = TreeForeignKey('self', null=True, blank=True, related_name='children', db_index=True)

    def __str__(self):
        return str(self.name)

    class MPTTMeta:
        level_attr = 'level'
        order_insertion_by = ['name']

    class Meta:
        verbose_name_plural = "Substance Categories"
        verbose_name = "Substance Category"


class HealthEffect(models.Model):
    file_id = models.IntegerField()
    name = models.CharField(max_length=500, null=True, blank=True)
    slug = models.SlugField(max_length=500, null=True, blank=True)
    description = models.TextField(default="", null=True, blank=True)

    def __str__(self):
        return str(self.name)

    def get_absolute_url(self):
        return reverse('chemical:health-effect', args=[str(self.slug)])


class Chemical(models.Model):
    RECOMMENDATION_STATUS = (
        ("default", "Default",),
        ("disallow_everywhere", "Disallow everywhere")
    )
    MERGING_STATUS = (
        ("not_merged", "Not Merged",),
        ("merged_from", "Merged From",),
        ("merged_to", "Merged To",),
    )
    name = models.CharField(max_length=500, null=True, blank=True)
    display_as = models.CharField(max_length=500, null=True, blank=True)
    slug = models.SlugField(max_length=500, null=True, blank=True)
    definition = RichTextField(default="", null=True, blank=True)
    # synonyms_list = models.ManyToManyField(ChemicalSynonym, blank=True, related_name='chemicals')
    synonyms = models.TextField(default="", null=True, blank=True)
    associated_from = models.CharField(max_length=255, null=True, blank=True)
    recommendation_status = models.CharField(choices=RECOMMENDATION_STATUS, default="default", max_length=255)
    merging_status = models.CharField(choices=MERGING_STATUS, default="not_merged", max_length=255)
    category_associated_from = models.TextField(default="", null=True, blank=True)
    categories = TreeManyToManyField(SubstanceCategory, related_name='chemicals', blank=True)
    chemical_number = models.CharField(max_length=255, null=True, blank=True)
    parent_chemical_numbers = models.TextField(null=True, blank=True)
    health_effects = models.ManyToManyField(HealthEffect, related_name='chemicals', blank=True)
    cas_rn = models.CharField(max_length=255, null=True, blank=True)
    drug_bank_ids = models.TextField(default="", null=True, blank=True)
    foodb_id = models.CharField(max_length=255, null=True, blank=True)
    name_scientific = models.CharField(max_length=500, null=True, blank=True)
    itis_id = models.CharField(max_length=500, null=True, blank=True)
    wikipedia_id = models.CharField(max_length=500, null=True, blank=True)
    picture_file_name = models.CharField(max_length=500, null=True, blank=True)
    picture_content_type = models.CharField(max_length=500, null=True, blank=True)
    picture_file_size = models.CharField(max_length=500, null=True, blank=True)
    t3db_id = models.CharField(max_length=500, null=True, blank=True)
    inchi_identifier = models.TextField(default='', null=True, blank=True)
    inchi_key = models.TextField(default='', null=True, blank=True)
    hmdb_id = models.TextField(default='', null=True, blank=True)
    pubchem_Compound_ID = models.TextField(default='', null=True, blank=True)
    chembl_id = models.TextField(default='', null=True, blank=True)
    chem_spider_id = models.TextField(default='', null=True, blank=True)
    kegg_compound_id = models.TextField(default='', null=True, blank=True)
    uni_prot_id = models.TextField(default='', null=True, blank=True)
    omim_id = models.TextField(default='', null=True, blank=True)
    chebi_id = models.TextField(default='', null=True, blank=True)
    bio_cyc_id = models.TextField(default='', null=True, blank=True)
    ctd_id = models.TextField(default='', null=True, blank=True)
    stitch_di = models.TextField(default='', null=True, blank=True)
    pdb_id = models.TextField(default='', null=True, blank=True)
    actor_id = models.TextField(default='', null=True, blank=True)

    affiliate_us = models.CharField(max_length=512, null=True, blank=True)
    affiliate_international = models.CharField(max_length=512, null=True, blank=True)
    selfhacked_link = models.CharField(max_length=512, null=True, blank=True)

    def synonyms_as_list(self):
        return self.synonyms.split('|')

    def __str__(self):
        return str(self.name)

    @property
    def display_name(self):
        return self.display_as if self.display_as else self.name

    def get_absolute_url(self):
        return reverse('chemical:chemical', args=[str(self.slug)])

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        # self.slug = get_random_string(length=32)
        model = super(Chemical, self).save(force_insert=False, force_update=False, using=None,
                                           update_fields=None)
        # self.slug = slugify(self.name)
        # if Chemical.objects.filter(slug=self.slug).exists():
        #     self.slug = "%s-%s" % (self.pk, self.slug,)
        super(Chemical, self).save(force_insert=False, force_update=False, using=None,
                                   update_fields=None)
        return model

    @property
    def display_description(self):
        t3db_data = self.t3db_data.first()
        return keeptags(t3db_data.description if t3db_data and t3db_data.description else self.definition, ("a",))

    class Meta:
        ordering = ['name']


class ChemicalT3DBData(models.Model):
    chemical = models.ForeignKey(Chemical, null=True, blank=True, related_name="t3db_data")
    name = models.TextField(default='', null=True, blank=True)
    chemical_class = models.TextField(default='', null=True, blank=True)
    description = RichTextField(default='', null=True, blank=True)
    types = models.TextField(default='', null=True, blank=True)
    synonyms = models.TextField(default='', null=True, blank=True)
    chemical_formula = models.TextField(default='', null=True, blank=True)
    average_molecular_mass = models.TextField(default='', null=True, blank=True)
    monoisotopic_mass = models.TextField(default='', null=True, blank=True)
    iupac_name = models.TextField(default='', null=True, blank=True)
    traditional_name = models.TextField(default='', null=True, blank=True)
    smiles = models.TextField(default='', null=True, blank=True)
    kingdom = models.TextField(default='', null=True, blank=True)
    super_class = models.TextField(default='', null=True, blank=True)
    primary_class = models.TextField(default='', null=True, blank=True)
    sub_class = models.TextField(default='', null=True, blank=True)
    direct_parent = models.TextField(default='', null=True, blank=True)
    alternate_parents = models.TextField(default='', null=True, blank=True)
    geometric_description = models.TextField(default='', null=True, blank=True)
    substituents = models.TextField(default='', null=True, blank=True)
    descriptors = models.TextField(default='', null=True, blank=True)
    status = models.TextField(default='', null=True, blank=True)
    origin = models.TextField(default='', null=True, blank=True)
    cellular_locations = models.TextField(default='', null=True, blank=True)
    biofluids = models.TextField(default='', null=True, blank=True)
    tissues = models.TextField(default='', null=True, blank=True)
    pathways = models.TextField(default='', null=True, blank=True)
    state = models.TextField(default='', null=True, blank=True)
    appearance = models.TextField(default='', null=True, blank=True)
    melting_point = models.TextField(default='', null=True, blank=True)
    boiling_point = models.TextField(default='', null=True, blank=True)
    solubility = models.TextField(default='', null=True, blank=True)
    log_p = models.TextField(default='', null=True, blank=True)
    route_of_exposure = RichTextField(default='', null=True, blank=True)
    mechanism_of_toxicity = models.TextField(default='', null=True, blank=True)
    metabolism = RichTextField(default='', null=True, blank=True)
    toxicity = models.TextField(default='', null=True, blank=True)
    lethal_dose = models.TextField(default='', null=True, blank=True)
    carcinogenicity = models.TextField(default='', null=True, blank=True)
    uses_sources = RichTextField(default='', null=True, blank=True)
    minimum_risk_level = models.TextField(default='', null=True, blank=True)
    health_effects = models.TextField(default='', null=True, blank=True)
    symptoms = RichTextField(default='', null=True, blank=True)
    treatment = RichTextField(default='', null=True, blank=True)
    wikipedia_link = models.TextField(default='', null=True, blank=True)
    drug_bank_id = models.TextField(default='', null=True, blank=True)


class ChemicalMechanismOfAction(models.Model):
    description = models.TextField(default='', null=True, blank=True)

    def __str__(self):
        return self.description


class Reference(models.Model):
    description = models.TextField(default='', null=True, blank=True)
    ref_id = models.CharField(max_length=500, null=True, blank=True)

    def __str__(self):
        return self.description


class Target(models.Model):
    biodb_id = models.CharField(max_length=500, null=True, blank=True)
    name = models.CharField(max_length=500, null=True, blank=True)
    uniprot_id = models.CharField(max_length=500, null=True, blank=True)
    gene = models.ForeignKey(Gene, null=True, blank=True, related_name='target')

    def __str__(self):
        return self.name


class ChemicalTargetMechanism(models.Model):
    chemical = models.ForeignKey(Chemical, null=True, blank=True, related_name='moas')
    mechanism_of_action = models.ForeignKey(ChemicalMechanismOfAction, null=True, blank=True, related_name='moas')
    target = models.ManyToManyField(Target, related_name='moas')
    reference = models.ManyToManyField(Reference, blank=True, related_name='moas')

    # def __str__(self):
    #     return self.reference


class ChemicalGeneInteractionType(models.Model):
    name = models.CharField(max_length=255, null=True, blank=True)
    code = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(default="", null=True, blank=True)
    parent_code = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return str(self.name)

    class Meta:
        ordering = ['name']


class Organism(models.Model):
    latin_name = models.CharField(max_length=255, null=True, blank=True)
    english_name = models.CharField(max_length=255, null=True, blank=True)
    slug = models.SlugField(max_length=512)
    scientific_name_full = models.CharField(max_length=512, null=True, blank=True)
    scientific_name = models.CharField(max_length=512, null=True, blank=True)
    common_name = models.CharField(max_length=512, null=True, blank=True)
    chinese_name = models.CharField(max_length=512, null=True, blank=True)
    genus = models.CharField(max_length=512, null=True, blank=True)
    species = models.CharField(max_length=512, null=True, blank=True)
    family = models.CharField(max_length=512, null=True, blank=True)
    itis_id = models.CharField(max_length=512, null=True, blank=True)
    food_group = models.CharField(max_length=512, null=True, blank=True)
    food_subgroup = models.CharField(max_length=512, null=True, blank=True)
    food_type = models.CharField(max_length=512, null=True, blank=True)
    country = models.CharField(max_length=512, null=True, blank=True)
    tcm_use = models.CharField(max_length=512, null=True, blank=True)
    definition = models.TextField(default='', null=True, blank=True)
    foodb_id = models.CharField(max_length=512, null=True, blank=True)
    ebi_icon_class = models.CharField(max_length=512, default='', null=True, blank=True)

    def __str__(self):
        return str(self.latin_name)

    class Meta:
        ordering = ['latin_name']


class Preparations(models.Model):
    name = models.CharField(max_length=512, null=True, blank=True)
    chebi_id = models.CharField(max_length=512, null=True, blank=True)
    info = models.TextField(default='')
    synonyms = models.TextField(default='')
    parent_hierarchy = models.CharField(max_length=512, null=True, blank=True)
    parent_id = models.CharField(max_length=512, null=True, blank=True)
    accessions = models.CharField(max_length=512, null=True, blank=True)
    food_group = models.CharField(max_length=512, null=True, blank=True)
    food_subgroup = models.CharField(max_length=512, null=True, blank=True)
    food_type = models.CharField(max_length=512, null=True, blank=True)
    foodb_id = models.CharField(max_length=512, null=True, blank=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = 'Preparations'


class ChemicalConcentration(models.Model):
    organism = models.ForeignKey("Organism", null=True)
    preparation = models.ForeignKey("Preparations", null=True)
    chemical = models.ManyToManyField("Chemical", related_name="concentrations")
    rel_type = models.CharField(max_length=255, null=True, blank=True)
    source_compound_id = models.CharField(max_length=255, null=True, blank=True)
    source_food_id = models.CharField(max_length=255, null=True, blank=True)
    orig_food_id = models.CharField(max_length=255, null=True, blank=True)
    orig_food_common_name = models.CharField(max_length=255, null=True, blank=True)
    orig_food_scientific_name = models.CharField(max_length=255, null=True, blank=True)
    orig_food_part = models.CharField(max_length=255, null=True, blank=True)
    orig_compound_id = models.CharField(max_length=255, null=True, blank=True)
    orig_compound_name = models.CharField(max_length=255, null=True, blank=True)
    conc = models.FloatField(null=True, blank=True)
    conc_min = models.FloatField(null=True, blank=True)
    conc_max = models.FloatField(null=True, blank=True)
    conc_unit = models.CharField(max_length=255, null=True, blank=True)
    citation = models.CharField(max_length=255, null=True, blank=True)
    citation_type = models.CharField(max_length=255, null=True, blank=True)
    orig_method = models.CharField(max_length=255, null=True, blank=True)
    orig_unit_expression = models.CharField(max_length=255, null=True, blank=True)
    ref_compound = models.CharField(max_length=255, null=True, blank=True)
    ref_food = models.CharField(max_length=255, null=True, blank=True)
    compound_id = models.CharField(max_length=255, null=True, blank=True)
    related_item_id = models.CharField(max_length=255, null=True, blank=True)
    unified_concentration = models.FloatField(null=True, blank=True)


class ChemicalGeneInteraction(models.Model):
    gene = models.ForeignKey(Gene)
    chemical = models.ForeignKey(Chemical)
    organism = models.ForeignKey(Organism, null=True, blank=True)
    interaction = models.TextField(default="", null=True, blank=True)
    pub_med_ids = models.CharField(max_length=255, null=True, blank=True)
    amount = models.IntegerField(default=0)
    references = models.TextField(default="", null=True, blank=True)

    def pub_med_ids_as_list(self):
        if self.references:
            return self.references.split('\n')
        else:
            pub_med_ids = self.pub_med_ids.split('|')
            return ['https://www.ncbi.nlm.nih.gov/pubmed/{}'.format(id) for id in pub_med_ids]

    def __str__(self):
        return str(self.interaction)


class ChemicalGeneInteractionAction(models.Model):
    INTERACTION_ACTIONS = (
        ("affects", "Affects",),
        ("increases", "Increases",),
        ("decreases", "Decreases",),
    )
    interaction = models.ForeignKey(ChemicalGeneInteraction, related_name='actions')
    interaction_type = models.ForeignKey(ChemicalGeneInteractionType)
    action = models.CharField(choices=INTERACTION_ACTIONS, max_length=255)

    def __str__(self):
        return str(self.interaction)


class ChemicalDiseaseInteraction(models.Model):
    chemical = models.ForeignKey("Chemical")
    disease = models.ForeignKey(DiseaseTrait)
    cas_rn = models.CharField(max_length=255, null=True, blank=True)
    direct_evidence = models.TextField(default='')
    inference_gene = models.ForeignKey(Gene, null=True, blank=True)
    inference_score = models.FloatField(null=True, blank=True, default=0)
    omim_ids = models.TextField(default='')
    pub_med_ids = models.TextField(default='')


class ChemicalPathway(models.Model):
    chemical = models.ForeignKey("Chemical", related_name="pathways")
    cas_rn = models.CharField(max_length=255, null=True, blank=True)
    pathway_name = models.TextField(default='')
    pathway_id = models.CharField(max_length=255, null=True, blank=True)
    related_pathway = models.ForeignKey("genome.Pathway", null=True, blank=True)
    p_value = models.TextField(default='')
    corrected_p_value = models.TextField(default='')
    target_match_qty = models.IntegerField(default=0)
    target_total_qty = models.IntegerField(default=0)
    background_match_qty = models.IntegerField(default=0)
    background_total_qty = models.IntegerField(default=0)

# class ChemicalOrganismInteraction(models.Model):
