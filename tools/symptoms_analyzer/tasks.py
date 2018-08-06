from django.core.cache import cache
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from sqlalchemy import and_

from genome.helpers import execute_sqla_query
from genome.models import SnpStudy, Snp, SnpAllele, SnpGenes, Gene
from genome.tasks import app
from tools.common_func import create_gwas_dict, rec_dd, check_task_active_scheduled
from tools.symptoms_analyzer.data_read import setup_indiv_dict


@app.task
def prepare_pickle_data():
    # creates and save GWAS study dictionary
    study_dict = create_gwas_dict(SnpStudy.objects.all())
    cache.set('SCA_GWAS_DATA', study_dict)

    # get snps list with relative gene name
    snps = execute_sqla_query(
        Snp.sa.query(
            Snp.sa.id,
            Snp.sa.rsid,
            Snp.sa.importance,
            Snp.sa.minor_allele,
            Snp.sa.major_allele,
            Snp.sa.description_advanced,
            Gene.sa.name
        ).filter(
            Snp.sa.rsid.isnot(None)
        ).join(
            SnpGenes.sa, and_(SnpGenes.sa.snp_id == Snp.sa.id)
        ).outerjoin(
            Gene.sa, and_(Gene.sa.id == SnpGenes.sa.gene_id)
        )
    )

    # set up the description dictionaries for both snp data types. result saved to the compressed file.
    snp_alleles = SnpAllele.objects.exclude(snp__rsid__isnull=True).exclude(snp__rsid__exact='').values_list(
        'description_minor',
        'description_major',
        'description_hetero',
        'snp__rsid',
        'category_id'
    )

    desc_d = setup_indiv_dict(rec_dd(), snp_alleles, True)
    desc_d = setup_indiv_dict(desc_d, snps, False)

    cache.set('SCA_SNP_DATA', desc_d)

    # creates and saves the category/snp data dictionaries
    snp_data = dict()
    for snp in snps:
        snp_data[snp.rsid] = {
            'Gene': snp.name,
            'Imp': snp.importance,
            'Minor': snp.minor_allele,
            'Major': snp.major_allele,
        }

    cache.set('SCA_OUT_DATA', snp_data)

    return True


@receiver(post_save, sender=Snp)
@receiver(post_delete, sender=Snp)
@receiver(post_save, sender=SnpAllele)
@receiver(post_delete, sender=SnpAllele)
def update_search_data(sender, instance, **kwargs):
    in_progress, logs = check_task_active_scheduled('tools.symptoms_analyzer.tasks.prepare_pickle_data')

    if not in_progress:
        prepare_pickle_data.apply_async(countdown=60 * 60)
    else:
        print('already scheduled, skip search data files update...')
