from app.config import BASE_PATH
from gensim.models import Word2Vec



def test():
    model = loadModel()
    return model.wv.most_similar(positive=['php'])
    
def get_similar(positive, negative):
    model = loadModel()
    if not isinstance(positive, list):
        positive = [positive]
    
    if negative and not isinstance(negative, list):
        negative = [negative]
    else:
        negative = []
    
    return model.wv.most_similar(positive=positive,negative=negative)
    

model = None

def loadModel():
    global model
    if model is None:
        model = Word2Vec.load(BASE_PATH + "/../pretrained/word2vecrecruitskills.model")
    
    return model
