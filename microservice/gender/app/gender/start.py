from flair.data import Sentence
from flair.models import TextClassifier
from app.logging import logger
from app.config import BASE_PATH

classifier = None

def loadModel():
    global classifier
    if not classifier:
        classifier = TextClassifier.load(BASE_PATH + '/../pretrained/gender/flair/taggers/gender/final-model.pt')
    
    return classifier


def classify(name):
    logger.info("recieved %s" , name)
    classifier = loadModel()
    sentence = Sentence(name.lower().strip())
    classifier.predict(sentence)
    logger.info("predicted %s",sentence.labels)
    return sentence.labels[0].value, sentence.labels[0].score
