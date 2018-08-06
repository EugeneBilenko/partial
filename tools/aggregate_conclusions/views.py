from django.http import JsonResponse
from django.shortcuts import render
from rest_framework import viewsets
from rest_framework.response import Response

from genome.models import SnpStudy
from .models import TraitMatches
from .queries import LIST_TRAIT_MATCHES
from .serializers import TraitMatchesSerializer
from .tasks import calculate_cores


class TraitMarchesView(viewsets.ViewSet):

    @staticmethod
    def __parse_matches(match):
        if not match:
            return []
        r = match.strip('[').strip(']').split(',')
        if len(r) > 3:
            result = {
                'genotype': r[0],
                'rsid': r[1],
                'minor_allele': r[2],
                'id': r[3]
            }

            count = r[0].count(r[2] or '')

            if r[0] == '--':
                result['order'] = 5  # badge-default

            elif not result['genotype'] or not count:
                result['order'] = 0  # badge-success

            elif not r[2]:
                result['order'] = 3  # badge-purple
                result['order'] = 4  # badge-info

            elif count == 1:
                result['order'] = 1  # badge-warning

            elif count >= 2:
                result['order'] = 2  # badge-danger
        else:
            result = r

        return result

    def list(self, request):
        result = []
        criteria = {'file': self.request.user.user_profile.active_file}
        file = request.user.user_profile.active_file
        limit = request.GET.get('limit', 15)
        offset = request.GET.get('offset', 0)
        ethnicity = request.GET.get('ethnicity', 'ALL').upper()
        parent = request.GET.get('parent', '')

        if parent:
            if parent == 'No category':
                parent = ''

            criteria['p_term'] = parent
            parent = "AND UPPER(tm.p_term::text) = UPPER('{0}')".format(parent)

        try:
            c_min = (int(request.GET.get('min', '')) - 1) * 10
            criteria['score__gt'] = c_min
        except ValueError:
            c_min = 0

        try:
            c_max = int(request.GET.get('max', '')) * 10
            criteria['score__lte'] = c_min
        except ValueError:
            c_max = 100

        try:
            count = int(request.GET.get('count', ''))
            criteria['m_count__gte'] = count
        except ValueError:
            count = 0

        query = LIST_TRAIT_MATCHES.format(file.id, ethnicity, limit, offset, count, c_min, c_max, parent)

        for p in TraitMatches.objects.raw(query):
            data = [self.__parse_matches(i) for i in p.snps]
            ids = [i['id'] for i in data]

            tm = TraitMatches.objects.get(pk=p.id)

            cc = tm.dt_ontology.filter(is_excluded_from_gwas=False).count()

            result.append({
                'name': p.name,
                'count': p.count,
                'score': p.score,
                'id': p.id,
                'm_count': p.m_count,
                'avg_score': (p.avg_score or 0) * 100.0,
                'matches': data,
                'other': SnpStudy.objects.filter(
                    diseasestrait_text=p.name
                ).exclude(
                    snp_id__in=ids
                ).values_list('snp__rsid', flat=True),
            })

        count = TraitMatches.objects.filter(**criteria).count()

        return Response({'count': count, 'results': result})


class TraitDetailsView(viewsets.ModelViewSet):
    queryset = TraitMatches.objects.all()
    serializer_class = TraitMatchesSerializer

    def get_serializer_context(self):
        return {'profile': self.request.user.user_profile}


class TraitMatchesParentViewSet(viewsets.ViewSet):
    def list(self, request):
        queryset = list(TraitMatches.objects.filter(
            file=self.request.user.user_profile.active_file
        ).order_by('p_term').values_list('p_term', flat=True).distinct())

        if len(queryset) and not queryset[0]:
            queryset[0] = 'No category'

        return Response({'results': queryset})


def get_genome_conclusions(request):
    """
    function return generated the aggregate conclusions data from an individual’s SNP data
    :param request
    :return: HttpResponse
    """
    profile = request.user.user_profile
    file = profile.active_file

    if profile.has_processing_file:
        return render(request, 'conclusions/disabled.html')

    if not file.agg_data_available:
        calculate_cores.delay(file)

    return render(request, 'conclusions/index.html')


def check_current_file_state(request):
    return JsonResponse({
        'status': request.user.user_profile.active_file.agg_data_available == 2
    })
