from app import es
from app.config import IS_DEV
from datetime import datetime


def createIndex():
    if IS_DEV:
        indexName = "devresume"
    else:
        indexName = 'resume'

    es.indices.create(index=indexName, ignore=400)


def addDoc(mongoid, lines):
    if IS_DEV:
        indexName = "devresume"
    else:
        indexName = 'resume'

    es.index(index=indexName, id=mongoid, body={
             "resume": " ".join(lines), 
             "timestamp": datetime.now()})


def deleteDoc(mongoid):
    if IS_DEV:
        indexName = "devresume"
    else:
        indexName = 'resume'

    es.delete(index=indexName, id=mongoid)


def searchDoc(searchText):
    if IS_DEV:
        indexName = "devresume"
    else:
        indexName = 'resume'

    es.search(
        index=indexName,
        body={
            "query":
                {
                    "match":
                    {
                        "resume":  searchText
                    }
                }
        }
    )
