from django.db import models
import requests


class Gptnation(models.Model):
    NATION = models.CharField(max_length=255)
    X_PASSWORD = models.CharField(max_length=255)
    USERAGENT = models.CharField(max_length=255, default='DarcOS')

    def __str__(self):
        return self.NATION

    def get_nation_issues(self):
        url = "https://www.nationstates.net/cgi-bin/api.cgi"
        headers = {
            "X-Password": self.X_PASSWORD,
            "User-Agent": self.USERAGENT or "DarcOS",
        }
        params = {
            "nation": self.NATION,
            "q": "issues",
        }
        response = requests.get(url, headers=headers, params=params, timeout=30)
        return response.text
