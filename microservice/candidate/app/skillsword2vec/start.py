from app.config import BASE_PATH
from gensim.models import Word2Vec
from app.logging import logger
import os
import json

model = {}
def loadModel(domain):
    domain = domain.replace(" ","")
    global model
    if domain not in model:

        dirs = os.listdir(BASE_PATH + "/../pretrained/word2vec/domainspecific/")
        for folder in dirs:
            folder2 = folder.replace(" ","")
            if folder2 == domain:

                logger.info("loading model... %s" , BASE_PATH + "/../pretrained/word2vec/domainspecific/"+folder+"/work2vecskill.bin")
                model[domain] = {}
                model[domain]['model'] = Word2Vec.load(BASE_PATH + "/../pretrained/word2vec/domainspecific/"+folder+"/work2vecskill.bin")

                with open(BASE_PATH + "/../pretrained/word2vec/domainspecific/"+folder+"/features.list") as json_file:
                    features = json.load(json_file)
                
                model[domain]['features'] = features
                break
    
    return model[domain]['model'] , model[domain]['features']
