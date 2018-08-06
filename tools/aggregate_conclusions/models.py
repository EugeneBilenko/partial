from django.db import models
from django.db.models.signals import post_save
from django.dispatch.dispatcher import receiver
from django.utils.translation import ugettext_lazy as _


# Create your models here.
class TraitMatches(models.Model):
    count = models.IntegerField(
        verbose_name=_('GWAS studies count'),
        help_text=_('the number of entries this trait has within the GWAS data file'),
        default=0
    )
    file = models.ForeignKey(
        verbose_name=_('genome file'),
        to='genome.File',
        related_name='trait_matches'
    )
    score = models.DecimalField(
        verbose_name=_('agg. score'),
        help_text=_('the trait’s overall aggregate score'),
        max_digits=20,
        decimal_places=2,
        default=0.0
    )
    p_term = models.CharField(
        verbose_name=_('parent term'),
        max_length=255,
        null=True,
        blank=True
    )
    name = models.CharField(
        verbose_name=_('disease/trait'),
        max_length=512
    )
    dt_ontology = models.ManyToManyField(
        to='genome.DiseaseTrait',
        related_name='trait_matches',
        verbose_name='Diseases/Traits_Ontology',
        blank=True
    )
    m_count = models.IntegerField(
        verbose_name=_('SNP Matches count'),
        default=0
    )

    def __str__(self):
        return '{0} (agg. score: {1})'.format(self.name, self.score)

    class Meta:
        ordering = ('id',)
        verbose_name = _('trait match')
        verbose_name_plural = _('User trait matches')


class SnpMatches(models.Model):
    trait = models.ForeignKey(
        verbose_name=_('trait match'),
        to=TraitMatches,
        related_name='matches'
    )
    m_type = models.IntegerField(
        verbose_name=_('the allele match type'),
        help_text=_('=1 for Heterozygous, =2 for Homozygous, =3 if missing'),
        default=3
    )
    risk_allele = models.CharField(
        verbose_name=_('Risk allele'),
        max_length=2,
        blank=True,
        null=True,
    )
    c_type = models.CharField(
        verbose_name=_('OR or BETA'),
        max_length=4,
        blank=True,
        null=True,
    )
    score = models.DecimalField(
        verbose_name=_('aggregated score (ScoreM)'),
        help_text=_('the individual aggregate score for the matching SNP'),
        max_digits=20,
        decimal_places=2
    )
    user_snp = models.ForeignKey(
        verbose_name=_('User SNP'),
        help_text=_('the SNP RSID # relative to the user genome file'),
        to='genome.UserRsid',
        related_name='related_matches',
        on_delete=models.CASCADE
    )
    snp = models.ForeignKey(
        verbose_name=_('SNP'),
        to='genome.Snp',
        related_name='related_matches',
        blank=True,
        null=True
    )

    def __str__(self):
        return '{0}-{1}'.format(self.rsid, self.risk_allele)

    class Meta:
        verbose_name = _('snp match')
        verbose_name_plural = _('User snp matches')


@receiver(post_save, sender=SnpMatches)
def manage_snp_matches(instance, **kwargs):
    trait = instance.trait
    trait.m_count = SnpMatches.objects.filter(trait=trait).count()
    trait.save()
