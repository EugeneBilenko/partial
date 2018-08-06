import csv

import pandas
from django.core.management import BaseCommand
from django.db.models import Q

from chemical.models import *


class Command(BaseCommand):
    help = "Update genes - add gene symbol, synonyms, fullname"

    def add_arguments(self, parser):
        parser.add_argument('--file', type=str)

    def handle(self, *args, **options):

        with open(options.get('file')) as f:
            lines = f.read().splitlines()
        count = len(lines)
        i = 0
        for line in lines:
            i += 1
            print("%s of %s" % (i, count))
            line = line.strip()
            if not line:
                continue
            Chemical.objects.filter(Q(name__startswith=line) | Q(name__endswith=line) |
                                    Q(synonyms__startswith=line) | Q(synonyms__endswith=line) |
                                    Q(synonyms__contains="|" + line) | Q(synonyms__contains=line + "|")).update(
                associated_from=line)
