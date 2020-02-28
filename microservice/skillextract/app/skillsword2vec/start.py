from app.config import BASE_PATH
from gensim.models import Word2Vec
from app.logging import logger


model = None
def loadModel():
    global model
    if model is None:
        logger.info("loading model... %s" , BASE_PATH + "/../pretrained/word2vec/word2vecrecruitskills.bin")
        model = Word2Vec.load(BASE_PATH + "/../pretrained/word2vec/word2vecrecruitskills.bin")
    
    return model
