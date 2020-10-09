from app.config import SEARCH_URL
from elasticsearch import Elasticsearch

es = None
def init_elastic_search():
    global es
    if es is None:
        es = Elasticsearch(SEARCH_URL)
    return es
