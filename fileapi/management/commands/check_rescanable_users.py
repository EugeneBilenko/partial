import os
import re
import time

import math

import datetime

import boto3
from django.contrib.auth.models import User
from django.core.management import BaseCommand

from genome.models import File
from genome.tasks import AWS_ACCESS_KEY_ID
from genome.tasks import S3_USE_SIGV4, AWS_SECRET_ACCESS_KEY


def remining_time(count, end="\n"):
    remining_time.i += 1
    cur_time = time.monotonic()
    if cur_time - remining_time.start_time >= 1 or remining_time.i >= count:
        remining_time.start_time = cur_time
        i_per_sec = remining_time.i - remining_time.last_i
        remining_time.last_i = remining_time.i
        time_remaining = (count - remining_time.i) / i_per_sec
        time_remaining = datetime.timedelta(seconds=math.floor(time_remaining))
        print("Time left %s" % time_remaining, end=" | ")
        print("%s rows per second" % i_per_sec, end=" | ")
        print("%s/%s" % (remining_time.i, count,), end=end)
        if remining_time.i >= count:
            remining_time.start_time = 0
            remining_time.last_i = 0
            remining_time.i = 0
remining_time.start_time = 0
remining_time.last_i = 0
remining_time.i = 0


os.environ['S3_USE_SIGV4'] = S3_USE_SIGV4
os.environ["AWS_ACCESS_KEY_ID"] = AWS_ACCESS_KEY_ID
os.environ["AWS_SECRET_ACCESS_KEY"] = AWS_SECRET_ACCESS_KEY
s3_client = boto3.client('s3')


class Command(BaseCommand):
    help = "Check each user file for ability to rescan it"

    def handle(self, *args, **options):
        files = File.objects.select_related().all()

        print("Get all files from bucket...")
        s3_files = []
        paginator = s3_client.get_paginator("list_objects")
        iterator = paginator.paginate(Bucket="decodify")
        for page in iterator:
            s3_files += page['Contents']
        print("Total files: %s" % len(s3_files))

        sub_compiled = re.compile(r'(\.txt|\.zip|\.txt\.zip)$')

        count = files.count()

        for file in files:
            remining_time(count)
            if file.file_name.startswith("23andMe_Connect_"):
                file.rescan_available = True
                file.provider = 2
                file.service = 1
            else:
                file_name = file.file_name
                for obj in s3_files:
                    key = obj["Key"]
                    file_name = sub_compiled.sub('', file_name)
                    key_clean = sub_compiled.sub('', key)
                    # {id}__{filename|clear}.{txt.zip|zip}
                    if not file_name.startswith(str(file.user_id)):
                        pattern = "%s__%s" % (file.user_id, file_name,)
                    else:
                        pattern = file_name
                    if pattern.lower() in key_clean.lower():
                        file.rescan_available = True
                        file.provider = 1
                        file.original_name = key
                        file.hashed_name = key
                        file.save()
                        break
                    file.rescan_available = False
            file.save()
