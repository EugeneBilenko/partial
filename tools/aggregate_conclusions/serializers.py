from django.db.models import Avg
from django.db.models.functions import Greatest
from rest_framework import serializers

from .models import TraitMatches
from decodify.aggregators import JsonAgg
from genome.models import DiseaseTrait, Gene, Snp, PopulationGenome
from genome.templatetags.genome_tags import sort_genotype, combined_risk_alleles, allele_flag


class DiseaseTraitOntology(serializers.ModelSerializer):
    class Meta:
        model = DiseaseTrait
        fields = ('definition', 'name')


class TraitMatchesSerializer(serializers.ModelSerializer):
    matches = serializers.SerializerMethodField()
    dt_ontology = DiseaseTraitOntology(many=True, read_only=True)

    def get_matches(self, obj):
        user = self.context['profile'].user
        bookmarked = self.context['profile'].bookmarked_snps.values_list('rsid', flat=True)
        data = obj.matches.values(
            'snp__importance',
            'user_snp__genotype',
            'snp__rsid',
            'snp__minor_allele',
            'snp__name',
            'snp__red_flag',
            'snp_id'
        )

        res = {}

        for i in data:
            snpstudies = Snp.objects.filter(id=i['snp_id']).annotate(
                snpstudies=JsonAgg(
                    "studies__risk_allele", "studies__risk_allele_frequency",
                    "studies__diseasestraits__name", "studies__p_value",
                    distinct=True
                )
            ).values_list('snpstudies', flat=True)[0]

            # check if SNP is auto flagged
            red_flag = allele_flag({
                'user': user
            }, {
                'red_flag': i['snp__red_flag'],
                'snpstudies': snpstudies,
                'minor_allele': i['snp__minor_allele'],
                'user_genotype': i['user_snp__genotype']
            }, None, False)

            pg = PopulationGenome.objects.filter(
                snp_id=i['snp_id'],
                abbr=self.context.get('ethnicity', 'ALL')
            ).annotate(
                max_risk=Greatest('homozygous_minor_freq', 'homozygous_major_freq', 'heterozygous_freq')
            ).aggregate(
                avg_max=Avg('max_risk')
            )

            res[i['snp__rsid']] = {
                'red_flag': red_flag,
                'importance': i['snp__importance'],
                'genotype': i['user_snp__genotype'],
                'name': i['snp__name'],
                'sort_genotype': sort_genotype(i['user_snp__genotype'], i['snp__minor_allele']),
                'risk_all_desc': combined_risk_alleles(snpstudies, i['user_snp__genotype'], True).replace('<br>', '\n'),
                'frequency': '{0:.1f}'.format((pg['avg_max'] or 0) * 100),
                'is_bookmarked': i['snp__rsid'] in bookmarked
            }

        return res

    def _get_snps_genes(self, snps):
        """
        Get list of genes for given SNPs
        :type snps: list[Snp]
        :rtype: dict[str] = Gene
        """
        genes = Gene.objects.filter(snps__pk__in=[snp['pk'] for snp in snps]).all()
        return {gene.name: gene for gene in genes}

    class Meta:
        model = TraitMatches
        fields = ('matches', 'dt_ontology')
