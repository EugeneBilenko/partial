import time
import datetime
import math

import itertools
from django.core.management import BaseCommand

from chemical.models import *


class Command(BaseCommand):

    def handle(self, *args, **options):
        toxins = SubstanceCategory.objects.filter(slug="toxins").first().get_family()
        chemicals = Chemical.objects.filter(categories__in=toxins)
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
        start_time = time.monotonic()
        last_i = 0
        i_per_sec = 0
        time_remaining = 0
        i = 0
        for chemical in chemicals:
            i += 1
            if time.monotonic() - start_time >= 1:
                start_time = time.monotonic()
                i_per_sec = i - last_i
                last_i = i
                time_remaining = (count - i) / i_per_sec
                time_remaining = datetime.timedelta(seconds=math.floor(time_remaining))
                print("Time left %s" % time_remaining, end=" ")
                print("%s rows per second" % i_per_sec, end=" ")
                print("%s/%s" % (i, count,))
            for drop_cat in rest:
                chemical.categories.remove(drop_cat)
