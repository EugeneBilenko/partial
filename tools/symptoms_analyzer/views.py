from django.core.cache import cache
from django.shortcuts import render, HttpResponse
from rest_framework import viewsets
from rest_framework.response import Response

from genome.models import Category
from tools.common_func import rec_dd, check_task_active_scheduled
from tools.symptoms_analyzer.tasks import prepare_pickle_data
from tools.symptoms_analyzer.text_match import det_best_user_match, det_user_snp_match


def index(request):
    return render(request, 'symptoms_analyzer/index.html')


def update_search_data(request):
    in_progress, logs = check_task_active_scheduled('tools.symptoms_analyzer.tasks.prepare_pickle_data')

    if not in_progress:
        prepare_pickle_data.delay()

    return HttpResponse('Processing data has {0} started<br><br>{1}'.format(
        'not' if in_progress else 'been',
        logs
    ))


class SCAViewSet(viewsets.ViewSet):
    @staticmethod
    def list(request):
        """
        Perform search logic for Symptoms Condition Analyzer
        :param request: HttpRequest object
        :return: searched results in json format
        """

        # initialisations
        search_term = request.GET.get('search', 'type 2 diabetes')
        user_snp_dict = rec_dd()
        in_progress, logs = check_task_active_scheduled('tools.symptoms_analyzer.tasks.prepare_pickle_data')

        # loads the sorted snp description dictionary (if not already loaded)
        descD = cache.get('SCA_SNP_DATA')
        # loads the output data (if not already loaded)
        snpD = cache.get('SCA_OUT_DATA')
        # loads the output data (if not already loaded)
        gwasD = cache.get('SCA_GWAS_DATA')

        # if some data is absent in cache start separate proc
        # ess to fill this data

        if not all([descD, snpD, gwasD]):
            if not in_progress:
                prepare_pickle_data.apply_async(countdown=1)
            uMatchR = None
        else:
            related_snps = request.user.user_profile.active_file.related_rsid.values_list(
                'rsid', 'genotype', 'id'
            )

            for rsid, genotype, pk in related_snps:
                user_snp_dict[rsid] = {'gene': genotype}

            # performs the fuzzy string match (calculates the search elapsed time)
            uMatch0 = det_best_user_match(search_term, descD, 10)
            uMatchR = det_user_snp_match(search_term, uMatch0, user_snp_dict, snpD, dict(gwasD))

        return Response({
            'search': search_term,
            'search_result': uMatchR,
            'categories': Category.objects.values('id', 'name'),
        })
