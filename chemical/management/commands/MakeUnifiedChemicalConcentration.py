from django.core.management import BaseCommand
from django.db import transaction
from django.db.models.functions import Lower

from chemical.models import *
from decodify.helpers import remaining_time


multiplier = {
    "aTE": 1,
    "ug_RAE": 1,
    "RE": 1,
    "kJ": 1,
    "NE": 1,
    "mg": 1,
    "kcal": 1,
    "g": 1000,
    "mg/100 g": 1,
    "IU": 1,
    "ug": 0.001,
    "ppm": 1,
    "": 1,
    "mg/100 ml": 1,
    "ug_DFE": 1
}


def chunks(l, n):
    """Yield successive n-sized chunks from l."""
    for i in range(0, len(l), n):
        yield l[i:i + n]


class Command(BaseCommand):
    help = "Update genes - add gene symbol, synonyms, fullname"

    def handle(self, *args, **options):

        concentrations = ChemicalConcentration.objects.only("conc", "conc_unit", "conc_max")
        cnt = concentrations.count()
        for chunk in chunks(concentrations, 2000):
            with transaction.atomic():
                for concentration in chunk:
                    remaining_time(cnt)
                    if concentration.conc > 0:
                        concentration.unified_concentration = concentration.conc * multiplier.get(concentration.conc_unit)
                    elif concentration.conc_max:
                        concentration.unified_concentration = concentration.conc_max * multiplier.get(concentration.conc_unit)
                    # chemical_name = concentration.orig_compound_name.lower()
                    # chemical = chemicals.get(chemical_name)
                    # if chemical:
                    #     concentration.chemical.add(chemical)
                    concentration.save()
        print("Success!")


