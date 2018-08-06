import time
import datetime
import math

import itertools
from django.core.management import BaseCommand
from django.db import transaction
from django.db.models import Q

from chemical.models import *
from decodify.helpers import remaining_time


class Command(BaseCommand):

    def handle(self, *args, **options):
        chemicals = Chemical.objects.filter(
            Q(name__iregex=r"(.+\-|.+\ ){4,}.+") |
            Q(name__iregex=r".*[\d].*[\-].*")
        ).all()
        obscure_category = SubstanceCategory.objects.filter(slug="obscure_chemicals").first()
        rest = [record.get_family() for record in SubstanceCategory.objects.filter(slug__in=[
            "popular-drugs",
            "natural-treatments",
            "beneficial-substances",
            "important-natural-compounds",
            "gras",
            "chemical_of_bilological_interest"
        ]).all()]
        rest = list(itertools.chain(*rest))

        chemicals = list(set(chemicals))
        count = len(chemicals)
        with transaction.atomic():
            for chemical in chemicals:
                remaining_time(count)
                chemical.categories.add(obscure_category)
                chemical.categories.remove(*rest)

        bio_interest = SubstanceCategory.objects.filter(slug="chemical_of_bilological_interest").first()
        chemicals = Chemical.objects.exclude(categories__in=obscure_category.get_family())
        count = len(chemicals)
        with transaction.atomic():
            for chemical in chemicals:
                remaining_time(count)
                chemical.categories.add(bio_interest)
