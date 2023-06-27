import sys
import imp
import os
import logging
from urllib.parse import urlparse

from scrapy.spiderloader import SpiderLoader
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

# Need to "mock" sqlite for the process to not crash in AWS Lambda / Amazon Linux
sys.modules["sqlite"] = imp.new_module("sqlite")
sys.modules["sqlite3.dbapi2"] = imp.new_module("sqlite.dbapi2")


def is_in_aws():
    logging.info('#### AWS_EXECUTION_ENV: %s' % os.getenv('AWS_EXECUTION_ENV'))
    return os.getenv('AWS_EXECUTION_ENV') is not None


def crawl(settings={}, spider_name="hamburg", spider_kwargs={}):
    project_settings = get_project_settings()
    spider_loader = SpiderLoader(project_settings)

    spider_cls = spider_loader.load(spider_name)

    feed_uri = ""
    feed_format = "jsonlines"

    try:
        spider_key = urlparse(spider_kwargs.get("start_urls")[0]).hostname if spider_kwargs.get(
            "start_urls") else urlparse(spider_cls.start_urls[0]).hostname
    except Exception:
        logging.exception("Spider or kwargs need start_urls.")

    if is_in_aws():
        # Lambda can only write to the /tmp folder.
        settings['HTTPCACHE_DIR'] = "/tmp"
        feed_uri = f"s3://{os.getenv('FEED_BUCKET_NAME')}/%(name)s/%(name)s-%(time)s.jsonl"
    else:
        feed_uri = f"file:///{os.path.join(os.getcwd(), 'data')}/%(name)s/%(name)s-%(time)s.jsonl"

    settings['FEED_URI'] = feed_uri
    settings['FEED_FORMAT'] = feed_format

    process = CrawlerProcess(settings={**project_settings, **settings})

    process.crawl(spider_cls, **spider_kwargs)
    process.start()


if __name__ == '__main__':
    if len(sys.argv) > 1:
        crawl(spider_name=sys.argv[1])
    else:
        crawl()