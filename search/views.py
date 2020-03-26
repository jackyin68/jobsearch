from django.shortcuts import render
from django.views.generic.base import View
from search.models import NlpJobType
from django.http import HttpResponse
import json
from elasticsearch import Elasticsearch
from datetime import datetime
import redis

redis_cli = redis.StrictRedis()
client = Elasticsearch(hosts=["127.0.0.1"])


class IndexView(View):
    def get(self, request):
        topn_search = redis_cli.zrevrangebyscore("search_keywords_set", "+inf", "-inf", start=0, num=5)
        topn_search = [search.decode(encoding='utf-8') for search in topn_search]
        return render(request, "index.html", {"topn_search": topn_search})


# Create your views here.
class SearchSuggest(View):
    def get(self, request):
        key_words = request.GET.get('s', '')
        re_datas = []
        if key_words:
            s = NlpJobType.search()
            s = s.suggest('mysuggest',
                          key_words,
                          completion={
                              'field': 'suggest',
                              'fuzzy': {"fuzziness": 2},
                              "size": 10
                          })
            suggestions = s.execute_suggest()
            if hasattr(suggestions, "mysuggest"):
                for match in suggestions.mysuggest[0].options:
                    source = match._source
                    re_datas.append(source["title"])

        return HttpResponse(json.dumps(re_datas), content_type="application/json")


# Create your views here.
class SearchView(View):
    def get(self, request):
        key_words = request.GET.get('q', '')
        # s_type = request.GET.get('s_type', 'jobinfo')
        redis_cli.zincrby("search_keywords_set", 1, key_words)
        topn_search = redis_cli.zrevrangebyscore("search_keywords_set", "+inf", "-inf", start=0, num=5)
        # topn_search_0 = topn_search[0].decode(encoding='utf-8')
        topn_search = [search.decode(encoding='utf-8') for search in topn_search]

        page = request.GET.get('p', '0')
        try:
            page = int(page)
        except:
            page = 0

        nlpjob_count = redis_cli.get("nlpjob_count").decode(encoding='utf-8')
        start_time = datetime.now()
        response = client.search(
            index="nlpjob",
            body={
                "query": {
                    "multi_match": {
                        "query": key_words,
                        "fields": ["title", "company", "location", "job_description"]
                    }
                },
                "from": page * 10,
                "size": 10,
                "highlight": {
                    "pre_tags": ['<span class="keyword">'],
                    "post_tags": ['</span>'],
                    "fields": {
                        "title": {},
                        "company": {},
                        "location": {},
                        "job_description": {},
                    }
                }
            }
        )
        end_time = datetime.now()
        last_time = (end_time - start_time).total_seconds()
        total_nums = response["hits"]["total"]
        if (total_nums % 10) > 0:
            page_nums = int(total_nums / 10) + 1
        else:
            page_nums = int(total_nums / 10)

        hit_list = []
        for hit in response["hits"]["hits"]:
            hit_dict = {}
            if "title" in hit["highlight"]:
                hit_dict["title"] = "".join(hit["highlight"]["title"])
            else:
                hit_dict["title"] = "".join(hit["_source"]["title"])

            if "company" in hit["highlight"]:
                hit_dict["company"] = "".join(hit["highlight"]["company"])
            else:
                hit_dict["company"] = "".join(hit["_source"]["company"])

            if "location" in hit["highlight"]:
                hit_dict["location"] = "".join(hit["highlight"]["location"])
            else:
                hit_dict["location"] = "".join(hit["_source"]["location"])

            if "job_description" in hit["highlight"]:
                hit_dict["job_description"] = "".join(hit["highlight"]["job_description"])
            else:
                hit_dict["job_description"] = "".join(hit["_source"]["job_description"])

            hit_dict["score"] = hit["_score"]
            hit_dict["url"] = hit["_source"]["url"]

            hit_list.append(hit_dict)

        return render(request, "search_result.html", {"page": page,
                                                      "total_nums": total_nums,
                                                      "last_time": last_time,
                                                      "all_hits": hit_list,
                                                      "key_words": key_words,
                                                      "page_nums": page_nums,
                                                      "nlpjob_count": nlpjob_count,
                                                      "topn_search": topn_search,
                                                      })


class LayoutView(View):
    def get(self, request):
        return render(request, "layout.html")
