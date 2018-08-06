import csv

import pandas
from django.core.management import BaseCommand
from django.db.models import Q
from django.utils.text import slugify

from chemical.models import *


class Command(BaseCommand):
    help = "Make Chemcial slug"

    def handle(self, *args, **options):
        chemicals = Chemical.objects.all()
        i = 0
        count = chemicals.count()
        for chemical in chemicals:
            i += 1
            print("%s of %s" % (i, count))
            chemical.slug = slugify(str(chemical.pk) + '-' + chemical.name)
            chemical.save()


