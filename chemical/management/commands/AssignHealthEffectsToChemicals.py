import csv

import time
import datetime
import math


import pandas
from django.core.management import BaseCommand
from django.db.models import Q

from chemical.models import *


class Command(BaseCommand):
    help = "Assign HealthEffect to Chemical - file compounds_health_effects.csv"

    def add_arguments(self, parser):
        parser.add_argument('--file', type=str)

    def handle(self, *args, **options):
        category = SubstanceCategory.objects.get(slug='important-natural-compounds')

        headers = {
            "id": str, "compound_id": str, "health_effect_id": str, "orig_health_effect_name": str,
            "orig_compound_name": str, "orig_citation": str, "citation": str, "citation_type": str, "created_at": str,
            "updated_at": str, "creator_id": str, "updater_id": str, "source_id": str, "source_type": str
        }
        data = pandas.read_csv(options.get('file'), header=0, delimiter=',', quoting=csv.QUOTE_ALL, dtype=headers)
        data.columns = [
            "id", "compound_id", "health_effect_id", "orig_health_effect_name", "orig_compound_name", "orig_citation",
            "citation", "citation_type", "created_at", "updated_at", "creator_id", "updater_id", "source_id",
            "source_type"
        ]

        data = data[["health_effect_id", "orig_health_effect_name", "orig_compound_name"]]
        groups = data.groupby("orig_compound_name").groups
        i = 0
        count = len(groups)
        start_time = time.monotonic()
        last_i = 0
        i_per_sec = 0
        time_remaining = 0
        for index, row in groups.items():
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

            chemicals = Chemical.objects.filter(
                Q(name__iexact=index) | Q(synonyms__iexact=index) |
                Q(synonyms__istartswith=index + "|") | Q(synonyms__iendswith="|" + index) |
                Q(synonyms__icontains="|" + index + "|")
            )
            if chemicals.exists():
                for chemical in chemicals.all():
                    if chemical.category_associated_from:
                        chemical.category_associated_from = ", ".join(
                            [index, chemical.category_associated_from])
                    else:
                        chemical.category_associated_from = index
                    chemical.save()
                    chemical.categories.add(category)
                    for index1 in row:
                        health_effect = HealthEffect.objects.get(file_id=data.ix[index1].health_effect_id)
                        chemical.health_effects.add(health_effect)
            else:
                continue

