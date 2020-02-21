from app.config import BASE_PATH
from gensim.models import Word2Vec
from app.logging import logger


def test():
    model = loadModel()
    return model.wv.most_similar(positive=['php'])
    
def get_similar(positive, negative, isGlobal = False):
    if isGlobal:
        model = loadGlobalModel()
    else:
        model = loadModel()

    if not isinstance(positive, list):
        positive = [positive]
    
    if negative and not isinstance(negative, list):
        negative = [negative]
    else:
        negative = []
    
    return model.wv.most_similar(positive=positive,negative=negative)
    

globalModel = None

def loadGlobalModel():
    global globalModel
    if globalModel is None:
        logger.info("loading model...")
        globalModel = Word2Vec.load(BASE_PATH + "/../pretrained/word2vecfull.bin")
    
    return globalModel

model = None
def loadModel():
    global model
    if model is None:
        logger.info("loading model...")
        model = Word2Vec.load(BASE_PATH + "/../pretrained/word2vecrecruitskills.bin")
    
    return model
