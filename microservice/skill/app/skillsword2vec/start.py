from app.config import BASE_PATH
from gensim.models import Word2Vec
from app.logging import logger


def test():
    model = loadModel()
    return model.wv.most_similar(positive=['php'])
    

model_words = []
global_model_words = []
def get_start_match(text, isGlobal = False, domain = None):
    if len(text) <= 2:
        # need atleast 2 letters for this to work
        return []

    text = text.replace(" ","_")

    global model_words
    global global_model_words
    
    model_words_to_use = []

    if isGlobal:
        model = loadDomainModel(domain)
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
    
    

def get_similar(positive, negative, domain = None):
    if domain:
        model = loadDomainModel(domain)
    else:
        model = loadModel()

    if not isinstance(positive, list):
        positive = [positive]
    
    if negative and not isinstance(negative, list):
        negative = [negative]
    else:
        negative = []
    
    return model.wv.most_similar(positive=positive,negative=negative)
    

def vec_exists(word, isGlobal = False, domain = None):
    if domain:
        model = loadDomainModel(domain)
    else:
        model = loadModel()
        
    try:
      model.wv.get_vector(word)
      return True
    except KeyError:
      return False

globalModel = {}
domainList = []

from os import walk
import glob

def get_domain_list():
    global domainList

    
    name_map = {
        "Teaching Education.bin" : "Education",
        "Sales.bin" : "Sales",
        "software development.bin": 'Software Development',
        "marketing.bin" : "Marketing",
        "legal.bin" :"Legal",
        "customer service.bin":"Customer Service",
        "HR Recruitment.bin": "HR Recruitment",
        "accounts.bin": "Accounts",
        "others" : "Others"
    }
    
    return name_map

def loadDomainModel(domain = None):
    global globalModel
    global domainList
    if not domain:
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
    else:
        if domain == "others":
            return loadModel()
        
        # if globalModel is None:
        #     logger.info("loading model... %s" , "/workspace/word2vec/word2vec/work2vecskillfull.bin")
        #     model = Word2Vec.load("/workspace/word2vec/word2vec/work2vecskillfull.bin")
        if domain in globalModel:
            return globalModel[domain]
        else:
            return None
    
    


model = None
def loadModel():
    global model
    if model is None:
        logger.info("loading model... %s" , "/workspace/word2vec/word2vec/work2vecskillfull.bin")
        model = Word2Vec.load("/workspace/word2vec/word2vec/work2vecskillfull.bin")
    return model
