import csv
import re
import pandas
from django.core.management import BaseCommand
from django.db import transaction
from django.db.models import Q

from chemical.models import *


class Command(BaseCommand):

    def handle(self, *args, **options):
        references = Reference.objects.all()
        pattern = re.compile(r"\(([\d]+)\)$")
        with transaction.atomic():
            for reference in references:
                str_search = pattern.search(reference.description)
                if bool(str_search):
                    reference.ref_id = str_search.group(1)
                    reference.save()