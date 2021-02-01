import json
import jsonlines

# this is data based from our ai recruit system

# {"line": "EDUCATIONAL QUALIFICATION WORK EXPERIENCE Avon Holidays Pvt. Ltd.- Sales & Marketing ( June, 2018- Currently working)", "tags": [{"ORG": "Avon Holidays Pvt. Ltd.-", "start_idx": 42, "tag": "ORG", "text": "Avon Holidays Pvt. Ltd.-"}, {"Designation": "Sales & Marketing", "start_idx": 67, "tag": "Designation", "text": "Sales & Marketing"}, {"DATE": "June, 2018- Currently", "start_idx": 87, "tag": "DATE", "text": "June, 2018- Currently"}]}


corpus = []

import unicodedata


def convert_file_to_conll(file):
    # try:
    training_data = []
    lines=[]
    skipped = 0

    error_candidates_list = [
        "5ea07aeb873f1f2c0b3661a6",
        '5eae0f126294bf0085672b04',
        '5ea079cb873f1f2c0b36616d',
        "5e985c50f754e812f459ce87"]  #this have some issue in db level
    # with open(file, 'r') as f:
    #     lines = f.readlines()

    lines = []
    with jsonlines.open(file) as reader:
        for data in reader:
            lines.append(data)

    
    no_lines = 0
    for line in lines:
    #     data = json.loads(line)

        # if data["candidateId"] in error_candidates_list:
        #     continue

        print("-----------------------")
        print(data)
        text = data['line']
        # if "  " in text:
        #     # unable to handle double space in a line right now 
        #     skipped += 1
        #     continue

        # text = text.replace(u'\xa0', u' ')
        text = text.encode('ascii', 'replace').decode().replace("?", " ")
        entities = {}
        text_length = len(text)

        charIdx2Wrd = {} #this will have mapping of idx to a word. so if specific index = 5 and it will tell if it word 0 or 1 or etc
        charIdx = 0
        wordIdx = 0
        wordmake = []

        wordList = text.split(" ")

        for char in text:
            if char == text[len(text) - 1]:
                charIdx2Wrd[charIdx] = wordIdx
                wordmake.append(char)
                if len(wordmake) > 0:
                    word = "".join(wordmake)

                    entities[wordIdx] = {
                        "word" : word.strip(),
                        "tag" : "O"
                    }

            if char == ' ':
                if len(wordmake) > 0:
                    word = "".join(wordmake)

                    entities[wordIdx] = {
                        "word" : word.strip(),
                        "tag" : "O"
                    }
                    # for idx in range(len(word)):
                    
                        # charIdx+=1

                wordIdx += 1
                wordmake = []
            else:
                charIdx2Wrd[charIdx] = wordIdx
                wordmake.append(char)

            charIdx+=1


        for annotation in data['tags']:
            
            start = annotation['start_pos']
            if start == -1:
                start = 0
            end = annotation['end_pos'] -1 #  -1 because usually len comes to a space and chartIdx2Wrd doesn't have space
            name = annotation['type']
            tagtext = annotation['text']

            if len(tagtext) == 0:
                continue

            if start != 0:
                print("tag text index start %s and end index %s", text.index(tagtext) , (text.index(tagtext) + len(tagtext)))

            if start in charIdx2Wrd:
                wordIdxstart = charIdx2Wrd[start]
            else:
                start_idx = text.index(tagtext)
                if abs(start_idx - start) == 1: # for some reason. index just varies by one
                    start = start_idx
                
                wordIdxstart = charIdx2Wrd[start]
                
                    

            if end in charIdx2Wrd:
                wordIdxend = charIdx2Wrd[end]
            else:
                end_idx = text.index(tagtext) + len(tagtext) -1 
                print("trying end idx %s", end_idx)
                if abs(end_idx - end) == 1:
                    end = end_idx
                
                wordIdxend = charIdx2Wrd[end]

            entities[wordIdxstart] = {
                "word" : entities[wordIdxstart]["word"],
                "tag" : name.strip()
            }

            entities[wordIdxend] = {
                "word" : entities[wordIdxend]["word"],
                "tag" : name.strip()
            }



        training_data.append(entities)


    print("skipped skipped %s", skipped)
    return training_data
    

corpus = convert_file_to_conll("ner-email-final.jsonl")
# print(training_data)

# exit


import random
import math

corpus_length = len(corpus)

print("total corpus" , corpus_length)

train_data_index = math.floor(corpus_length * .9)

train_data = corpus[0:train_data_index]
test_data = corpus[train_data_index:]

dev_data_index = math.floor(train_data_index * .9)

dev_data = train_data[dev_data_index:]
train_data = train_data[0:dev_data_index]

def write_lines_file(filename, entities):
    open(filename, 'w').close()
    with open(filename, 'a') as the_file:
        for entity in entities:
            for ent in entity:
                the_file.write(entity[ent]["word"] + "  " + entity[ent]["tag"] + "\n")

            the_file.write("\n")

write_lines_file('ner-email-final.jsonl.txt', corpus)
# write_lines_file('ner-train-v2.txt', train_data)
# write_lines_file('ner-test-v2.txt', test_data)
# write_lines_file('ner-dev-v2.txt', dev_data)