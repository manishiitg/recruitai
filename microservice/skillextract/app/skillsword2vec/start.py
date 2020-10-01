from app.config import BASE_PATH
from gensim.models import Word2Vec
from app.logging import logger


model = None
def loadModel():
    global model
    if model is None:
        logger.info("loading model... %s" , "/workspace/word2vec/word2vec/work2vecskillfull.bin")
        model = Word2Vec.load("/workspace/word2vec/word2vec/work2vecskillfull.bin")
    
    return model
