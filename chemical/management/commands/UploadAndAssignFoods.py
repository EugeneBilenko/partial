import csv

import time
import datetime
import math


import pandas
from django.core.management import BaseCommand
from django.db import transaction
from django.db.models import Q

from chemical.models import *


class Command(BaseCommand):
    help = "Assign HealthEffect to Chemical - file compounds_health_effects.csv"

    def add_arguments(self, parser):
        parser.add_argument('--file', type=str)

    def handle(self, *args, **options):
        category = SubstanceCategory.objects.get(slug='important-natural-compounds')

        headers = {
            "id": str,
            "name": str,
            "name_scientific": str,
            "description": str,
            "itis_id": str,
            "wikipedia_id": str,
            "picture_file_name": str,
            "picture_content_type": str,
            "picture_file_size": str,
            "picture_updated_at": str,
            "legacy_id": str,
            "food_group": str,
            "food_subgroup": str,
            "food_type": str,
            "created_at": str,
            "updated_at": str,
            "creator_id": str,
            "updater_id": str,
            "export_to_afcdb": str,
            "category": str
        }
        data = pandas.read_csv(options.get('file'), header=0, delimiter=',', quoting=csv.QUOTE_ALL, dtype=headers)
        data.columns = [
            "id",
            "name",
            "name_scientific",
            "description",
            "itis_id",
            "wikipedia_id",
            "picture_file_name",
            "picture_content_type",
            "picture_file_size",
            "picture_updated_at",
            "legacy_id",
            "food_group",
            "food_subgroup",
            "food_type",
            "created_at",
            "updated_at",
            "creator_id",
            "updater_id",
            "export_to_afcdb",
            "category"
        ]
        data1 = data.groupby("food_group")
        food_parent_category = SubstanceCategory.objects.get(slug='food')
        [SubstanceCategory(
            name=record,
            slug=slugify(record),
            parent=food_parent_category
        ).save() for record in data1.groups.keys()]
        counter_primary = len(data1.groups)
        counter_total = len(data)
        i = 0
        k = 0
        with transaction.atomic():
            for cat_name, indexes in data1.groups.items():
                i += 1
                counter_sub = len(indexes)
                j = 0
                category_to_assign = SubstanceCategory.objects.get(name=cat_name)
                sub_data = data.ix[indexes]
                for index, row in sub_data.iterrows():
                    k += 1
                    j += 1
                    print("group %s of %s" % (i, counter_primary))
                    print("compound %s of %s" % (j, counter_sub))
                    print("total %s of %s" % (k, counter_total))
                    chemicals = Chemical.objects.filter(
                        Q(name__iexact=row["name"]) | Q(synonyms__iexact=row["name"]) | Q(synonyms__istartswith=row["name"] + "|")
                        | Q(synonyms__iendswith="|" + row["name"]) | Q(synonyms__icontains="|" + row["name"] + "|")
                    )
                    if chemicals.exists():
                        for chemical in chemicals.all():
                            if chemical.category_associated_from:
                                chemical.category_associated_from = ", ".join([row["name"], chemical.category_associated_from])
                            else:
                                chemical.category_associated_from = row["name"]
                            if row["description"] != "":
                                if chemical.definition != "":
                                    chemical.definition = str(chemical.definition) + "\n" + str(row["description"])
                                else:
                                    chemical.definition = row["description"]
                            chemical.name_scientific = row["name_scientific"]
                            chemical.itis_id = row["itis_id"]
                            chemical.wikipedia_id = row["wikipedia_id"]
                            chemical.picture_file_name = row["picture_file_name"]
                            chemical.picture_file_size = row["picture_file_size"]
                            chemical.picture_content_type = row["picture_content_type"]
                            chemical.save()
                            chemical.categories.add(category_to_assign)
                    else:
                        chemical = Chemical.objects.create(
                            name=row["name"],
                            name_scientific=row["name_scientific"],
                            definition=row["description"],
                            itis_id=row["itis_id"],
                            wikipedia_id=row["wikipedia_id"],
                            picture_file_name=row["picture_file_name"],
                            picture_file_size=row["picture_file_size"],
                            picture_content_type=row["picture_content_type"]
                        )
                        chemical.save()
                        chemical.categories.add(category_to_assign)
