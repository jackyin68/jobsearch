from django.db import models

# Create your models here.
from datetime import datetime
from elasticsearch_dsl import DocType, Date, Nested, Boolean, \
    analyzer, Completion, Keyword, Text

from elasticsearch_dsl.analysis import CustomAnalyzer as _CustomAnalyzer

from elasticsearch_dsl.connections import connections
connections.create_connection(hosts=["localhost"])


class NlpCustomAnalyzer(_CustomAnalyzer):
    def get_analysis_definition(self):
        return {}


ik_analyzer = NlpCustomAnalyzer("ik_max_word", filter=["lowercase"])


class NlpJobType(DocType):
    suggest = Completion(analyzer=ik_analyzer)
    title = Text(analyzer="ik_max_word")
    company = Text(analyzer="ik_max_word")
    location = Text(analyzer="ik_max_word")
    job_description = Text(analyzer="ik_max_word")
    url = Text()

    class Meta:
        index = "nlpjob"
        doc_type = "jobinfo"


if __name__ == "__main__":
    NlpJobType.init()
