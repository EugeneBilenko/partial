import time
import datetime
import math

from django.core.management import BaseCommand

from chemical.models import *


class Command(BaseCommand):

    def handle(self, *args, **options):
        chemicals = Chemical.objects.all()
        count = len(chemicals)
        start_time = time.monotonic()
        last_i = 0
        i_per_sec = 0
        time_remaining = 0
        i = 0
        for chemical in chemicals:
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
            synonyms = chemical.synonyms.split("|")
            if len(synonyms) > 0:
                for synonym in synonyms:
                    new_synonym = ChemicalSynonym.objects.get_or_create(name=synonym)
                    chemical.synonyms_list.add(new_synonym[0])


