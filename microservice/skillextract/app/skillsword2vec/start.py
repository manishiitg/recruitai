from app.config import BASE_PATH
from gensim.models import Word2Vec
from app.logging import logger
import glob

globalModel = {}
domainList = []

def getDomainModel(domain = None):
    global globalModel
    global domainList
    logger.critical("domain: %s", domain)
    if not domain:
        return loadModel()
    if domain == "others":
        globalModel[domain] = loadModel()
    
    # if globalModel is None:
    #     logger.info("loading model... %s" , "/workspace/word2vec/word2vec/work2vecskillfull.bin")
    #     model = Word2Vec.load("/workspace/word2vec/word2vec/work2vecskillfull.bin")
    if domain in globalModel:
        return globalModel[domain]
    else:
        return loadModel()

def loadDomainModel(domain = None):
    global globalModel
    global domainList
    
    models = glob.glob("/workspace/word2vec/word2vec/*.bin")
    logger.critical(models)
    for model in models:
        if "-" not in model:
            continue
        else:
            domain = model.split("-")[1]
            domainList.append(domain)
            globalModel[domain] = Word2Vec.load(model)
    return globalModel
    
        

model = None
def loadModel():
    global model
    if model is None:
        logger.info("loading model... %s" , "/workspace/word2vec/word2vec/work2vecskillfull.bin")
        model = Word2Vec.load("/workspace/word2vec/word2vec/work2vecskillfull.bin")
    
    return model
