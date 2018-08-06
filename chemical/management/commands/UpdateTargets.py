import time
import datetime
import math

from django.core.management import BaseCommand
from django.db import transaction

from chemical.models import *


class Command(BaseCommand):

    def handle(self, *args, **options):
        targets = Target.objects.all()
        count = len(targets)
        start_time = time.monotonic()
        last_i = 0
        i_per_sec = 0
        time_remaining = 0
        i = 0
        with transaction.atomic():
            for target in targets:
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
                target.gene = Gene.objects.filter(synonyms__name__iexact=target.name).first()
                target.save()
