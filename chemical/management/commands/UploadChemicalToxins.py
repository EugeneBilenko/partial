import csv

import pandas
from django.core.management import BaseCommand
from django.db.models import Q

from chemical.models import *


class Command(BaseCommand):
    help = "Update genes - add gene symbol, synonyms, fullname"

    # def add_arguments(self, parser):
    #     parser.add_argument('--parent-mesh', type=str)
    #     parser.add_argument('--category', type=str)

    def update_chemicals(self, parent, category):
        chemicals = Chemical.objects.filter(parent_chemical_numbers__contains=parent)
        if chemicals.exists():
            for chemical in chemicals.all():
                chemical.categories.add(category)
                self.update_chemicals(chemical.chemical_number, category)
        else:
            return

    def handle(self, *args, **options):
        category = SubstanceCategory.objects.get(slug='toxins')

        self.update_chemicals('MESH:D014118', category)

