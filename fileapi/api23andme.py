import json

import os
import requests
from io import StringIO
from django.conf import settings


class Api23AndMe:
    api_base_url = "https://api.23andme.com"
    request_data = {
        'client_id': settings.X23ANDME_CLIENT_ID,
        'client_secret': settings.X23ANDME_CLIENT_SECRET,
        'redirect_uri': settings.X23ANDME_REDIRECT_URI,
    }

    def __init__(self, data=None):
        if data:
            self.request_data.update(data)

    def make_request(self, path, data=None, headers=None):
        if data is None:
            return requests.get("%s%s/" % (self.api_base_url, path,), headers=headers)
        else:
            request_data = self.request_data.copy()
            request_data.update(data)
            return requests.post("%s%s/" % (self.api_base_url, path,), data=request_data, headers=headers)

    def get_access_token(self, code, scope='basic genomes'):
        response = self.make_request("/token", {
            "code": code,
            'grant_type': 'authorization_code',
            'scope': scope,
        })
        return json.loads(response.text)

    def get_refresh_token(self, refresh_token, scope='basic genomes'):
        response = self.make_request("/token", {
            'grant_type': 'refresh_token',
            "refresh_token": refresh_token,
            'scope': scope,
        })
        return json.loads(response.text)

    def get_user(self, access_token):
        response = self.make_request("/1/user", headers={
            "Authorization": "Bearer " + str(access_token),
        })
        return json.loads(response.text)

    def get_genomes(self, access_token, profile_id):
        response = self.make_request("/1/genomes/%s/" % profile_id, headers={
            "Authorization": "Bearer " + str(access_token),
        })
        return json.loads(response.text)

    def get_snps_resources(self):
        file_name = "snps.b4e00fe1db50.data"
        file_path = "raw_data/%s" % file_name
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), file_path)
        return open(path)

        # response = requests.get("https://api.23andme.com/res/txt/")
        # return StringIO(response.text)
