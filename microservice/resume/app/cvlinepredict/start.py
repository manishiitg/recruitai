from app.config import BASE_PATH
from app.logging import logger
import re
import numpy as np
from pathlib import Path
from tokenizers import SentencePieceBPETokenizer
import os
import torch
from app.util import cleanMe
import torch.functional as F
from transformers import (WEIGHTS_NAME,
                                  BertForSequenceClassification,
                                  BertTokenizer)

from transformers import (WEIGHTS_NAME,
                                  DistilBertConfig,
                                  DistilBertForSequenceClassification,
                                  DistilBertTokenizer)

from transformers import (WEIGHTS_NAME,
                                  XLNetConfig,
                                  XLNetForSequenceClassification,
                                  XLNetTokenizer)

BASE_MODEL_PATH = BASE_PATH + "/../pretrained/cvpartsclassification/xlnet"
TOKENIZER_PATH = BASE_PATH + "/../pretrained/cvpartsclassification/"

logger.critical("xlnet base model path %s", BASE_MODEL_PATH)
logger.critical("tokenizer base model path %s", TOKENIZER_PATH)

sentPiecetokenizer = None
xlnetModel = None
xlnetTokenizer = None

device = 'cuda' if torch.cuda.is_available() else 'cpu'

def predict(text):
    # disable for now until we get proper model
    return ["", 0]
    
    do_eval = True
    xlnetModel, xlnetTokenizer = loadModel()
    sentPiecetokenizer = loadTokenizer()
    prob = torch.nn.Softmax()

    label_list = ['CONTACT', 'WRK', 'ENDINFO', 'PRJ', 'EDU', 'SKILL', 'INFO', 'SUMMARY']
    prediction =  False

    with torch.no_grad():
        if len(text) == 0:
            return False

        if len(text.split(" ")) < 10:
            return False

        if len(text) >= 200:
            text = text[:200]

        encoded = sentPiecetokenizer.encode(text)
        text = " ".join(encoded.tokens)

        input_ids = torch.tensor(xlnetTokenizer.encode(text, add_special_tokens=True)).unsqueeze(0)  # Batch size 1
        # print(input_ids)
        labels = torch.tensor([1]).unsqueeze(0)  # Batch size 1
        outputs = xlnetModel(input_ids.to(device), labels=labels.to(device))
        loss, logits = outputs[:2]

        
        probablity = prob(logits).squeeze().detach().cpu().numpy()
        # print(probablity)

        

        final_preds = []

        for index, p in enumerate(probablity):
            if p > .5:
                final_preds.append((p, label_list[index]))

        pred_index = np.argmax(logits.detach().cpu().numpy())

        # print(preds)

        
        logger.info("===================")
        logger.info(encoded.original_str)
        
        prediction = [label_list[pred_index] , str(probablity[pred_index])]

        if len(final_preds) > 1:
            for (p, label) in final_preds:
                logger.info("predicted %s with probablity %s", label , p)
        else:
            logger.info(" %s = = %s", label_list[pred_index] , probablity[pred_index])
        
        logger.info("===================")
    
    return prediction
        

def loadModel():
    global xlnetModel
    global xlnetTokenizer
    if not xlnetModel:
        
        # model_class = BertForSequenceClassification
        # tokenizer_class = BertTokenizer

        model_class = XLNetForSequenceClassification
        tokenizer_class = XLNetTokenizer

        args = {}
        # args["model_type"] = "bert"
        # args["model_name_or_path"] = BASE_MODEL_PATH #"bert-base-cased"
        # args["lower_case"] = False
        # args["output_dir"] = BASE_MODEL_PATH

        # args["model_type"] = "distilbert"
        # args["model_name_or_path"] = BASE_MODEL_PATH # "distilbert-base-uncased"
        # args["lower_case"] = False
        # args["output_dir"] = BASE_MODEL_PATH

        args["model_type"] = "xlnet"
        args["model_name_or_path"] = BASE_MODEL_PATH # "distilbert-base-uncased"
        args["lower_case"] = False
        args["output_dir"] = BASE_MODEL_PATH
        args["max_seq_length"] = 200

        xlnetTokenizer = tokenizer_class.from_pretrained(args["output_dir"], do_lower_case=args["lower_case"])
        
        xlnetModel = model_class.from_pretrained(args["output_dir"])
        xlnetModel.to(device)

    return xlnetModel, xlnetTokenizer


def loadTokenizer():
    global sentPiecetokenizer
    if not sentPiecetokenizer:
        logger.info("loading tokernizer from path %s", TOKENIZER_PATH)
        vocab = os.path.join(TOKENIZER_PATH, "tokenzier.txt-vocab.json")
        merges = os.path.join(TOKENIZER_PATH, "tokenzier.txt-merges.txt")

        sentPiecetokenizer = SentencePieceBPETokenizer(vocab, merges)
    
    return sentPiecetokenizer
