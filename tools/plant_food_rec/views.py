from django.http import JsonResponse

from chemical.models import Chemical
from tools.plant_food_rec.helpers import det_match_results


def index(request, pk):
    try:
        chemical = Chemical.objects.get(pk=pk)
        matched_data = det_match_results(chemical)
    except Chemical.DoesNotExist:
        matched_data = []

    return JsonResponse({'results': matched_data, 'count': len(matched_data)})
