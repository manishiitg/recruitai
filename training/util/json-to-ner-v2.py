import json

# this is data based from our ai recruit system

# {"line": "EDUCATIONAL QUALIFICATION WORK EXPERIENCE Avon Holidays Pvt. Ltd.- Sales & Marketing ( June, 2018- Currently working)", "tags": [{"ORG": "Avon Holidays Pvt. Ltd.-", "start_idx": 42, "tag": "ORG", "text": "Avon Holidays Pvt. Ltd.-"}, {"Designation": "Sales & Marketing", "start_idx": 67, "tag": "Designation", "text": "Sales & Marketing"}, {"DATE": "June, 2018- Currently", "start_idx": 87, "tag": "DATE", "text": "June, 2018- Currently"}]}


corpus = []

import unicodedata


def convert_file_to_conll(file):
    # try:
    training_data = []
    lines=[]
    with open(file, 'r') as f:
        lines = f.readlines()
    
    no_lines = 0
    for line in lines:
        data = json.loads(line)

        print(data)
        text = data['line']
        # text = text.replace(u'\xa0', u' ')
        text = text.encode('ascii', 'replace').decode().replace("?", " ")
        entities = []
        text_length = len(text)

        charIdx2Wrd = {} #this will have mapping of idx to a word. so if specific index = 5 and it will tell if it word 0 or 1 or etc
        charIdx = 0
        wordIdx = 0
        for word in text.split(" "):
            entities.append( {
                "word" : word.strip(),
                "tag" : "O"
            })
            for idx in range(len(word)):
                charIdx2Wrd[charIdx] = wordIdx
                charIdx+=1

            wordIdx += 1
            charIdx+=1  # due to space


        for annotation in data['tags']:

            start = annotation['start_pos']
            end = annotation['end_pos'] -1 #  -1 because usually len comes to a space and chartIdx2Wrd doesn't have space
            name = annotation['type']

            wordIdxstart = charIdx2Wrd[start]
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

    return training_data
    

training_data = convert_file_to_conll("v2.json1")
print(training_data)

exit


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
                the_file.write(ent + "\n")

            the_file.write("\n")

write_lines_file('ner-full-v2.txt', corpus)
write_lines_file('ner-train-v2.txt', train_data)
write_lines_file('ner-test-v2.txt', test_data)
write_lines_file('ner-dev-v2.txt', dev_data)