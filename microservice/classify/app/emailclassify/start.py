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
                                  XLNetConfig,
                                  XLNetForSequenceClassification,
                                  XLNetTokenizer)

BASE_MODEL_PATH = BASE_PATH + "/../pretrained/emailclassification/xlnet"
TOKENIZER_PATH = BASE_PATH + "/../pretrained/emailclassification/tokenizer"

logger.info("xlnet base model path %s", BASE_MODEL_PATH)
logger.info("tokenizer base model path %s", TOKENIZER_PATH)

sentPiecetokenizer = None
xlnetModel = None
xlnetTokenizer = None

device = 'cuda' if torch.cuda.is_available() else 'cpu'


def test():
    tokenizer = loadTokenizer()
    xlnetModel, xlnetTokenizer = loadModel()
    
    row = prepareData({
        "subject" : "resume(php developer)",
        "body" : "dear sir/madam,\n\nW.r.f to  your post on ur website.\nI have attached my resume within. Please have a look and respond\nwhether i will be able to fit in the position in your esteemed\norganisation.\n\nkind regards,\nNitika "
    })
    data = predict(xlnetModel, xlnetTokenizer, tokenizer,[row])
    return data    

def classifyData(data):
    tokenizer = loadTokenizer()
    xlnetModel, xlnetTokenizer = loadModel()
    inboxData = [prepareData(d) for d in data]
    data = predict(xlnetModel, xlnetTokenizer, tokenizer,inboxData)
    return data    

def predict(model,tokenizer, sentPiecetokenizer,inboxdata):
    # inboxdata is basically list of rows
    prob = torch.nn.Softmax()
    label_map = {'candidate': 0, 'other': 1}
    newlm = {}
    for key in label_map:
        newlm[label_map[key]] = key

    model.eval()

    ret = []
    with torch.no_grad():
        for row in inboxdata:
            text = row["text"]
            row = row["row"]
            
            if len(text) == 0:
                continue

            if len(text.split()) <= 1:
                print(text)
                print("very less words to predict")
                continue

            if len(text) > 511:
                text = text[0:511]


            encoded = sentPiecetokenizer.encode(text)
            
            input_ids = torch.tensor(tokenizer.encode(encoded.tokens, add_special_tokens=True)).unsqueeze(0)  # Batch size 1
            labels = torch.tensor([1]).unsqueeze(0)  # Batch size 1
            outputs = model(input_ids.to(device), labels=labels.to(device))
            loss, logits = outputs[:2]
            
            probablity = prob(logits).squeeze().cpu().numpy()

            final_preds = []

        
            pred_index = np.argmax(logits.detach().cpu().numpy())
            pred = {}
            

            # if len(final_preds) > 1:
            #   for (p, label) in final_preds:
            #     print("predicted ", label , "with probablity", p, " **************************")
            #     pred[label] = p
            # else:
            # print(newlm[pred_index], " = = ", probablity[pred_index], " ************** ")
            pred[newlm[pred_index]] = probablity.tolist()[pred_index]
            
            # print("===================")

            # print(row['_id'])
            if "ai" in row:
                row["ai"]["pipe1"] = pred
            else:
                row["ai"] = {
                    "pipe1" : pred
                }

            ret.append(row)

    return ret
            
        


def prepareData(row):
    # row = { body : "", subject : " "}

    body = cleanMe(row["body"])  
    words = body.split(" ")
    newwords = []
    for idx, word in enumerate(words):
        # CV multipart/alternative; text/plain; format=flowed; quoted-printable
        if word.find("multipart/alternative;") >= 0 or word.find("text/plain;") >= 0 or word.find("format=flowed;") >= 0 or word.find("quoted-printable") >= 0 or word.find("--=_") >= 0 or word.find("charset=") >= 0 or word.find('text/html;') == 0:
            continue

        if word.find("Content-Type:") >= 0 or word.find("Content-Transfer-Encoding:") >= 0:
            idx += 1
            continue
        
        newwords.append(word)

    body = " ".join(newwords)

    if "Content-Disposition: attachment;" in body:
    # print("ok this has attachment")
        body = body[: body.index("Content-Disposition: attachment;")  ]

    if "subject" in row:
        subject = row["subject"]
        content = subject + " " + body
  
    if len(content) > 512:
        content = content[:512]

    content = content.replace(u'\xa0', u' ').encode('ascii', 'ignore').decode()
    content = re.sub(' +', ' ', content)
    content = content.replace("\xc2\xa0", ' ')

    return {
      "text" : content,
      "row": row
    }


def loadModel():
    global xlnetModel
    global xlnetTokenizer
    if not xlnetModel:
        

        model_class = XLNetForSequenceClassification
        tokenizer_class = XLNetTokenizer

        args = {}
        args["model_type"] = "xlnet"
        args["model_name_or_path"] = "xlnet-base-cased"
        args["lower_case"] = False
        args["output_dir"] = BASE_MODEL_PATH

        xlnetTokenizer = tokenizer_class.from_pretrained(args["output_dir"], do_lower_case=args["lower_case"])
        
        xlnetModel = model_class.from_pretrained(args["output_dir"])
        xlnetModel.to(device)

    return xlnetModel, xlnetTokenizer


def loadTokenizer():
    global sentPiecetokenizer
    if not sentPiecetokenizer:
        logger.info("loading tokernizer from path %s", TOKENIZER_PATH)
        vocab = os.path.join(TOKENIZER_PATH, "sentpiece-vocab.json")
        merges = os.path.join(TOKENIZER_PATH, "sentpiece-merges.txt")

        sentPiecetokenizer = SentencePieceBPETokenizer(vocab, merges)
    
    return sentPiecetokenizer
