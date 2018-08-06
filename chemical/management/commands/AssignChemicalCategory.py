import time
import datetime
import math

from django.core.management import BaseCommand
from django.db import transaction
from django.db.models import Q

from chemical.models import *


class Command(BaseCommand):
    help = "Add chemical category - files natural.txt, popular_drugs.txt"

    def add_arguments(self, parser):
        parser.add_argument('--file', type=str)
        parser.add_argument('--category', type=str)

    def handle(self, *args, **options):
        category = SubstanceCategory.objects.get(slug=options.get('category'))

        with open(options.get('file')) as f:
            lines = f.read().splitlines()
        count = len(lines)
        start_time = time.monotonic()
        last_i = 0
        i_per_sec = 0
        time_remaining = 0
        i = 0
        chemicals_to_save = []
        for line in lines:
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
            line = line.strip()
            if not line:
                continue
            chemicals = Chemical.objects.filter(
                Q(name__iexact=line) | Q(synonyms__iexact=line) | Q(synonyms__istartswith=line + "|")
                | Q(synonyms__iendswith="|" + line) | Q(synonyms__icontains="|" + line + "|")
            ).all()
            for chemical in chemicals.all():
                if chemical.category_associated_from:
                    chemical.category_associated_from = ", ".join([line, chemical.category_associated_from])
                else:
                    chemical.category_associated_from = line
                chemicals_to_save.append(chemical)

        with transaction.atomic():
            for chemical in chemicals_to_save:
                chemical.save()
                chemical.categories.add(category)
                print("success")

