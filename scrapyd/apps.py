from django.apps import AppConfig


class ScrapydConfig(AppConfig):
    name = 'scrapyd'
    verbose_name = "Scrapyd"

    def ready(self):
        """Override this to put in:
            Users system checks
            Users signal registration
        """
        pass
