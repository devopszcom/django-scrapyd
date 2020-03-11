================
Django scrapyd
================

Django scrapyd is a Django app to manage scrapyd (Scrapy Deploy)

Quick start
-----------
1. Install

    `pip install django-scrapyd==0.2`

2. Add "django-scrapyd" to your INSTALLED_APPS setting like this::

    INSTALLED_APPS = [
        ...
        'scrapyd',
    ]

3. Run `python manage.py migrate` to create the django-scrapyd models.
