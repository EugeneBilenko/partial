import time
import datetime
import math

from django.core.management import BaseCommand
from django.db import transaction
from django.db.models import Q

from chemical.models import *
from decodify.helpers import remaining_time


class Command(BaseCommand):
    help = "Add chemical category - files natural.txt, popular_drugs.txt"

    def add_arguments(self, parser):
        parser.add_argument('--file', type=str)

    def handle(self, *args, **options):
        categories = SubstanceCategory.objects.filter(slug__in=[
            "natural-treatments",
            "beneficial-substances",
            "important-natural-compounds",
            "chemical_of_bilological_interest"
        ]).all()
        with open(options.get('file')) as f:
            lines = f.read().splitlines()
        count = len(lines)
        with transaction.atomic():
            for line in lines:
                remaining_time(count)
                line = line.strip()
                if not line:
                    continue
                chemicals = Chemical.objects.filter(
                    Q(name__iexact=line) | Q(synonyms__iexact=line) | Q(synonyms__istartswith=line + "|")
                    | Q(synonyms__iendswith="|" + line) | Q(synonyms__icontains="|" + line + "|")
                ).all()
                for chemical in chemicals.all():
                    chemical.categories.add(*categories)

