from django.contrib import admin
from . import models

from django.urls import path
from django.utils.html import format_html
from django.http.response import HttpResponse
from datetime import datetime
from django.contrib import messages
from django.template.response import TemplateResponse
from django.shortcuts import redirect
import requests
import re
import json
import logging

from .scrapyd import ScraydAPI

logger = logging.getLogger("django")


@admin.register(models.CrawlerNode)
class CrawlerNodeAdmin(admin.ModelAdmin):
    list_display = ('name', 'host', 'port', 'status')

    def status(self, obj):
        return format_html('<a href="/admin/scrapyd/crawlernode/status/{}">status</a>'.format(obj.id))

    status.short_description = 'Status'

    def get_urls(self):
        urls = super(CrawlerNodeAdmin, self).get_urls()
        my_urls = [
            path('status/run-spider/<int:cid>/<str:spider>',
                 self.admin_site.admin_view(self.run_spider),
                 name="run_spider"),
            path('status/stop-spider/<int:cid>/<str:job_id>', self.admin_site.admin_view(self.cancel_job_view),
                 name="stop_job"),
            path('status/<int:cid>', self.admin_site.admin_view(self.status_view)),
            path('logs/stats/<int:cid>/<str:spider>/<str:job_id>', self.admin_site.admin_view(self.log_stats_view)),
            path('logs/detail/<int:cid>/<str:spider>/<str:job_id>', self.admin_site.admin_view(self.log_detail_view)),
        ]
        return my_urls + urls

    def status_view(self, request, cid):
        crawler = models.CrawlerNode.objects.get(pk=cid)
        scrapy_client = ScraydAPI(host=crawler.host, port=crawler.port)

        jobs = scrapy_client.listjobs()
        jobs['finished'] = list(reversed(jobs['finished']))[:15]
        for job in jobs['finished']:
            during = datetime.strptime(job["end_time"], "%Y-%m-%d %H:%M:%S.%f") - datetime.strptime(
                job["start_time"], "%Y-%m-%d %H:%M:%S.%f")
            job["during"] = during.total_seconds() / 60

        spiders = scrapy_client.listspiders()["spiders"]

        context = dict(
            # Include common variables for rendering the admin template.
            self.admin_site.each_context(request),
            # Anything else you want in the context...
            cid=cid,
            status=scrapy_client.daemonstatus(),
            jobs=jobs,
            spiders=spiders,
            log_url="http://{}:{}/logs/default".format(crawler.host, crawler.port),
        )
        return TemplateResponse(request, "scrapyd/status.html", context)

    def run_spider(self, request, cid, spider):
        try:
            try:
                params = request.GET.get('params', None)
                args = {}
                if params:
                    peices = params.split(",")
                    for item in peices:
                        temp = item.strip().split("=")
                        args[temp[0].strip()] = temp[1].strip()
            except Exception:
                raise Exception("Parse params error")

            crawler = models.CrawlerNode.objects.get(pk=cid)
            scrapy_client = ScraydAPI(host=crawler.host, port=crawler.port, spider=spider)
            response = scrapy_client.schedule(args=args)

            msg = 'Job id: {}'.format(response["jobid"])
            if params:
                msg += '. Params: {}'.format(params)
            messages.add_message(request, messages.SUCCESS, msg)
        except Exception as e:
            messages.add_message(request, messages.ERROR, "Error: {}".format(str(e)))
        return redirect("/admin/scrapyd/crawlernode/status/{}".format(cid))

    def cancel_job_view(self, request, cid, job_id):
        try:
            crawler = models.CrawlerNode.objects.get(pk=cid)
            scrapy_client = ScraydAPI(host=crawler.host, port=crawler.port)
            response = scrapy_client.cancel(job_id=job_id)
            if response["status"] == "ok":
                msg = 'Closing Job id: {}'.format(job_id)
                messages.add_message(request, messages.SUCCESS, msg)
            else:
                msg = "Error: {}".format(str(response))
                messages.add_message(request, messages.ERROR, msg)
        except Exception as e:
            logger.exception(e)
            messages.add_message(request, messages.ERROR, "Error: {}".format(str(e)))
        return redirect("/admin/scrapyd/crawlernode/status/{}".format(cid))

    def log_stats_view(self, request, cid, spider, job_id):
        try:
            crawler = models.CrawlerNode.objects.get(pk=cid)
            url = "http://{}:{}/logs/default/{}/{}.log".format(crawler.host, crawler.port, spider, job_id)
            response = requests.get(url)
            content = response.text
            matches = re.search(r"Dumping Scrapy stats:(.*)\d\d\d\d-\d\d", content.replace("\n", ""))
            stats = matches.group(1)

            stats = re.sub(r'(?is)(datetime\.datetime\([\d\,\s]+\))', r'"\1"', stats).replace("'", '"')
            stats = json.loads(stats)

            result = {
                "result": {
                    "item_scraped_count": 0,
                    "response_received_count": 0,
                    "finish_reason": ""
                },
                "downloader": {},
                "log_count": {},
                "scheduler": {},
                "item_scraped_count": 0,
                "finish_reason": "",
                "more": {},
            }
            for k, v in stats.items():
                if k.startswith("downloader"):
                    result["downloader"][k[11:]] = v
                elif k.startswith("log_count"):
                    result["log_count"][k[10:]] = v
                elif k.startswith("scheduler"):
                    result["scheduler"][k[10:]] = v
                elif k in result['result'].keys():
                    result['result'][k] = v
                else:
                    if k in ['start_time', 'finish_time']:
                        # result["more"][k] = str(eval(v))
                        continue
                    else:
                        result["more"][k] = v

            return TemplateResponse(request, "scrapyd/log_stats.html", {"data": result})
        except Exception as e:
            # logger.exception(e)
            raise e

    def log_detail_view(self, request, cid, spider, job_id):
        crawler = models.CrawlerNode.objects.get(pk=cid)
        url = "http://{}:{}/logs/default/{}/{}.log".format(crawler.host, crawler.port, spider, job_id)
        response = requests.get(url)
        content = response.text
        return HttpResponse(content, content_type='text/plain')
