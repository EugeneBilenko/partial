import csv

import pandas
from django.core.management import BaseCommand
from django.db import transaction
from django.db.models import Q
from django.db.models.functions import Lower

from chemical.models import *
from decodify.helpers import remaining_time
from genome.models import DiseaseHierarchy


def chunks(l, n):
    """Yield successive n-sized chunks from l."""
    for i in range(0, len(l), n):
        yield l[i:i + n]


class Command(BaseCommand):
    help = "Update genes - add gene symbol, synonyms, fullname"

    def handle(self, *args, **options):

        concentrations = ChemicalConcentration.objects.only("orig_compound_name")
        chemicals = dict(Chemical.objects.annotate(name_lower=Lower('name')).values_list('name_lower', 'id'))
        cnt = concentrations.count()
        for chunk in chunks(concentrations, 2000):
            with transaction.atomic():
                for concentration in chunk:
                    remaining_time(cnt)
                    chemical_name = concentration.orig_compound_name.lower()
                    chemical = chemicals.get(chemical_name)
                    if chemical:
                        concentration.chemical.add(chemical)
        print("Success!")


