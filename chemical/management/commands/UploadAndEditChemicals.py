import csv
import json

import pandas
from django.core.management import BaseCommand
from django.db.models import Q

from chemical.models import *


class Command(BaseCommand):
    help = "Update genes - add gene symbol, synonyms, fullname"

    def add_arguments(self, parser):
        parser.add_argument('--file', type=str)

    def handle(self, *args, **options):
        category = SubstanceCategory.objects.get(slug='beneficial-substances')

        data = open(options.get('file')).read()
        json_data = json.loads(data)
        count = len(json_data)
        i = 0
        for struct in json_data:
            i += 1
            print("%s of %s" % (i, count))
            if struct['type'] == 'chemical':
                Chemical.objects.filter(
                    Q(name__contains=struct['title']) |
                    Q(synonyms__contains=struct['title'])).update(category=category)
