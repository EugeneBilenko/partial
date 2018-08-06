import csv
import json

import pandas
import time
import datetime
import math

from django.core.management import BaseCommand
from django.db.models import F
from django.db.models import Q

from chemical.models import *


class Command(BaseCommand):
    help = "Assign Benificial Substance category --file substances.json"

    def add_arguments(self, parser):
        parser.add_argument('--file', type=str)

    def handle(self, *args, **options):
        category = SubstanceCategory.objects.get(slug='beneficial-substances')

        data = open(options.get('file')).read()
        json_data = json.loads(data)
        count = len(json_data)
        i = 0

        start_time = time.monotonic()
        last_i = 0
        i_per_sec = 0
        time_remaining = 0

        for struct in json_data:
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
            if struct['type'] == 'chemical':
                chemicals = Chemical.objects.filter(
                    Q(name__iexact=struct['title']) | Q(synonyms__iexact=struct['title']) |
                    Q(synonyms__istartswith=struct['title'] + "|") | Q(synonyms__iendswith="|" + struct['title']) |
                    Q(synonyms__icontains="|" + struct['title'] + "|")
                ).all()
                for chemical in chemicals.all():
                    if chemical.category_associated_from:
                        chemical.category_associated_from = ", ".join([struct['title'], chemical.category_associated_from])
                    else:
                        chemical.category_associated_from = struct['title']
                    chemical.save()
                    chemical.categories.add(category)

