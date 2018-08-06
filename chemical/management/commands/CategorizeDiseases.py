import csv

import pandas
from django.core.management import BaseCommand
from django.db import transaction
from django.db.models import Q

from chemical.models import *
from genome.models import DiseaseHierarchy


class Command(BaseCommand):
    help = "Update genes - add gene symbol, synonyms, fullname"

    def update_chemicals(self, parent, category):
        diseases = DiseaseTrait.objects.filter(ctd_parent_ids__contains=parent)
        if diseases.exists():
            for disease in diseases.all():
                # disease.categories.add(category)
                current = DiseaseHierarchy.objects.create(
                    disease=disease,
                    parent=category
                )

                self.update_chemicals(disease.ctd_id, current)
        else:
            return

    def handle(self, *args, **options):
        with transaction.atomic():
            parents = DiseaseTrait.objects.filter(ctd_parent_ids="MESH:C")
            for parent in parents:
                parent_node = DiseaseHierarchy.objects.create(
                    disease=parent
                )
                self.update_chemicals(parent.ctd_id, parent_node)




