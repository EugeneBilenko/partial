from collections import defaultdict

import numpy
from django.db.models import Count

from genome.models import SnpStudy
from genome.tasks import app
from tools.common_func import create_gwas_dict, match_single_snp
from .calc_scores import calc_agg_scores
from .models import TraitMatches, SnpMatches


@app.task
def calculate_cores(file):
    file.agg_data_available = 1
    file.save()

    disease_matches = defaultdict(dict)
    related_snps = file.related_rsid.values_list('rsid', 'genotype', 'id')

    if not len(related_snps):
        file.agg_data_available = 2
        file.save()
        return False

    snp_list = numpy.array(related_snps)
    study_query = SnpStudy.objects.filter(snp__rsid__in=snp_list[:, 0])

    dt_d = study_query.extra(
        select={'dt': 'diseasestrait_text'}
    ).values('dt', 'parent_term').annotate(count=Count('diseasestrait_text'))

    for i in dt_d:
        disease_matches[i['dt']] = {
            'Count': i['count'],
            'pTerm': i['parent_term'] or '',
            'Match': []
        }

    # create GWAS studies dict with depth level
    study_dict = create_gwas_dict(study_query)

    # searches for all snp matches
    disease_matches = match_single_snp(disease_matches, snp_list, study_dict)

    # calculates the aggregate scores
    dt = calc_agg_scores(disease_matches)
    sm = []
    for i in dt:
        match = dt[i]['Match']

        if not len(match):
            continue

        tm = TraitMatches.objects.filter(
            p_term=dt[i]['pTerm'],
            count=dt[i]['Count'],
            file=file,
            name=i
        ).first()

        if not tm:
            dt_ontology = list(SnpStudy.objects.get(
                pk=match[0]['studyId']
            ).diseasestraits.filter(
                is_excluded_from_gwas=False
            ).values_list('id', flat=True))

            if len(dt_ontology):
                tm = TraitMatches.objects.create(
                    score=dt[i]['Score'],
                    p_term=dt[i]['pTerm'],
                    count=dt[i]['Count'],
                    m_count=len(match),
                    name=i,
                    file=file
                )
                tm.dt_ontology.add(*dt_ontology)
        else:
            dts = tm.dt_ontology.filter(is_excluded_from_gwas=False).count()
            if dts:
                tm.score = dt[i]['Score']
                tm.matches.all().delete()
                tm.m_count = len(match)
                tm.save()
            else:
                tm.delete()

        if tm:
            for j in match:
                sm.append(SnpMatches(
                    trait=tm,
                    m_type=j['mType'],
                    risk_allele=j['gType'],
                    c_type=j['cType'],
                    snp_id=j['snpId'],
                    score=j['ScoreM'],
                    user_snp_id=j['userSnpId'],
                ))

    SnpMatches.objects.bulk_create(sm)

    file.agg_data_available = 2
    file.save()

    return True
