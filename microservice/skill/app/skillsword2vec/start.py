from app.config import BASE_PATH
from gensim.models import Word2Vec
from app.logging import logger


def test():
    model = loadModel()
    return model.wv.most_similar(positive=['php'])
    

model_words = []
global_model_words = []
def get_start_match(text, isGlobal = False):
    if len(text) <= 2:
        # need atleast 2 letters for this to work
        return []

    text = text.replace(" ","_")

    global model_words
    global global_model_words
    
    model_words_to_use = []

    if isGlobal and False:
        model = loadGlobalModel()
        if len(global_model_words) == 0:    
            for word in model.wv.vocab:
                global_model_words.append(word + "")

        model_words_to_use = global_model_words
                
    else:
        model = loadModel()
        if len(model_words) == 0:    
            for word in model.wv.vocab:
                model_words.append(word + "")

        model_words_to_use = model_words

    ret = []
    start_ret = []
    for word in model_words_to_use:
        if word.lower().find(text.lower()) == 0:
            start_ret.append({
                "word" : word,
                "count" : model.wv.vocab[word].count
            })

        if text.lower() in word.lower():
            ret.append({
                "word" : word,
                "count" : model.wv.vocab[word].count
            })


    if len(start_ret) > 0:
        return sorted(start_ret, key=lambda k: k['count']) 
    return sorted(ret, key=lambda k: k['count'])
    
    

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

def vec_exists(word, isGlobal = False):
    if isGlobal:
        model = loadGlobalModel()
    else:
        model = loadModel()
    try:
      model.wv.get_vector(word)
      return True
    except KeyError:
      return False

def loadGlobalModel():
    global globalModel
    if globalModel is None:
        logger.info("loading model... %s", BASE_PATH + "/../pretrained/word2vec/word2vecfull.bin")
        globalModel = Word2Vec.load(BASE_PATH + "/../pretrained/word2vec/word2vecfull.bin")
    
    return globalModel

model = None
def loadModel():
    global model
    if model is None:
        logger.info("loading model... %s" , BASE_PATH + "/../pretrained/word2vec/word2vecrecruitskills.bin")
        model = Word2Vec.load(BASE_PATH + "/../pretrained/word2vec/word2vecrecruitskills.bin")

    

    return model
