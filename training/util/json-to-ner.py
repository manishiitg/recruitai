import json

# this is for the initial system were we tagging for entire cv.

# {"id": 972, "text": "Urshila Lohani\nSenior Corporate Account Executive - MongoDB\n\nGurgaon, Haryana - Email me on Indeed: indeed.com/r/Urshila-Lohani/ab8d3dc6dd8b13f0\n\nWilling to relocate: Anywhere\n\nWORK EXPERIENCE\n\nSenior Corporate Account Executive\n\nMongoDB -  Gurgaon, Haryana -\n\nMay 2016 to Present\n\n• Designed and implemented a 2-year sales strategy for South India Region; revenues grew 4X.\n• Trained sales team of 35 from 20 partner companies; revenues generated through partners\nincreased 50%.\n• Led Business development team of 5 to build pipeline of 4X.\n• Acquired 32 new accounts with industry leaders including Intuit, IBM, Wipro, McAfee, Airtel,\nReligare and Adobe; 100% renewals in all existing accounts.\n• Initiated, designed and executed marketing events; attendees included 200 IT heads;\ngenerated $1M\npipeline.\n• Ranked in top 5% of global sales team of 322; Awarded thrice for highest quarterly revenues\nin APAC.\n• Won Excellence Club Award in FY17 and FY18.\n\nAccount Manager\n\nRed Hat -  Bengaluru, Karnataka -\n\nJune 2014 to May 2016\n\n• Responsible for sales of entire Red Hat Product Portfolio in Mid market and Enterprise Accounts\nin West and South India Region.\n• Introduced Customer Success Program; renewals up 20%; revenues rose 12%.\n• Formulated sales strategies and achieved $4M in sales.\n• Won multiple awards (four quarters - highest revenues closed) and (2 consecutive years - 100%\nClub Award).\n• Improved brand presence in small cities and towns; inducted new partners; revenue driven\nby partner\nchannels up 26%\n• Designed events engaging IT Directors & CxOs; penetrated 7 key accounts; generated $400K\npipeline.\n\nAccount Manager\n\nOracle -  Noida, Uttar Pradesh -\n\nMay 2013 to May 2014\n\nhttps://www.indeed.com/r/Urshila-Lohani/ab8d3dc6dd8b13f0?isid=rex-download&ikw=download-top&co=IN\n\n\nBusiness Development Rep\n\nOracle -\n\nSeptember 2011 to April 2013\n\n• Responsible for MySQL, Oracle Linux and VM Sales in North Central US Region.\n• Generate opportunities using Linkedin, Hoovers, Job Portals, Marketing Leads and Oracle Install\nbase.\n• Work closely with Channel Partners, Resellers and Oracle Internal Counterparts to increase\ncustomer base.\n• Designed & developed Pipeline Generation kits for Sales team of 12.\n• Awarded in Q1 and Q2 FY13 for highest quarterly achievement in the team; 100% Annual Quota\nachieved for FY12 and FY13.\n• Revamped email marketing campaigns led to 15% higher response rate.\n• Initiated a structured mentorship program for MySQL Team; Training times down by 2 Months;\nproductivity\nup 50%.\n\nEDUCATION\n\nB Tech Honors in Technical\n\nCollege of Engineering -  Roorkee, Uttarakhand\n\nAugust 2007 to May 2011", "meta": {}, "annotation_approver": null, "labels": [[0, 14, "Name"], [15, 49, "Designation"], [194, 228, "Designation"], [230, 238, "Worked At"], [974, 981, "Worked At"], [1796, 1820, "Designation"], [2540, 2546, "Designation"], [2568, 2590, "College"]]}


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
        text = data['text']
        # text = text.replace(u'\xa0', u' ')
        text = text.encode('ascii', 'replace').decode().replace("?", " ")
        entities = []
        text_length = len(text)
        indexes = []

        # print(text_length, " : " , data["id"])
        for i in range(text_length):
            indexes.append("O")
        
        if len(data['labels']) == 0:
            print("no labels skipping!")
            continue


        for annotation in data['labels']:

            start = annotation[0]
            end = annotation[1]
            name = annotation[2]

            # print("name ", name, " text: ", text[start:end])

            if end > text_length:
                print(data["id"], " id: this is a problem! indexes is more than texxt length. tag name:", name, "start: " , start, "end: ", end, "text length: ", text_length)
                continue

            for j in range(start, end):
                indexes[j] = name


        # logic i am thinking is 
        # need to make proper logical statements from the cv so that ai 
        # can learn better and mainly reuse the rnn hidden state properly
        # basically if we look at the a cv it organized into different parts like
        # exp, contact, skills etc 
        # we need to some how divide it into logic parts i think he will help the rnn train better
        # 
        # 
        # logic i am think is
        # make a sentense if it is very short, less than 3 words add next sentnce to it 
        # else we will assume it a full logical sentense thats it 
        # we will use break points like multiple occurance of \n\n\n to break sentence \t will be taken as space # only      
        # ... as of 29th Jan this is fully done with detectron2 and ocr help
        word = ""
        entity_type = indexes[0]
        multiple_n_count = 0
        text = text.replace("\t"," ") # # we assume \t is same as space only

        max_n_count = 2
        max_seq_len = 50
        multiple_n_count = 0
        min_seq_length = 10

        count = 0
        for i in range(text_length):
            char = text[i]


            if char == "\n":
                count += 1
        
            if count > max_n_count:
                max_n_count = count
            else:
                count = 0

        if max_n_count > 3:
            max_n_count = 3

        # basically max_n_count will be between 2-3 depending how may actually are there

        assert len(text) == text_length

        for i in range(text_length):

            char = text[i]

            if char == "\n":
                multiple_n_count += 1

                if len(entities) > max_seq_len:
                    corpus.append(entities)
                    entities = []

            else:
                multiple_n_count = 0

            if multiple_n_count >= max_n_count:
                if len(entities)  > min_seq_length:
                    corpus.append(entities)
                    entities = []

                continue

            if char == "\n":
                if len(word.strip()) > 0:
                    entities.append( word.strip() + "  " + entity_type )
                word = ""
                # entities.append( ".  O" )
                entity_type = "O"
            else:
                if char == " ":
                    if len(word.strip()) > 0:
                        entities.append( word.strip() + "  " + entity_type )
                    word = ""
                else:
                    if indexes[i] != entity_type and len(word.strip()) > 0:
                        if len(word.strip()) > 0:
                            entities.append( word.strip() + "  " + entity_type )
                        entity_type = indexes[i]
                        word = ""
                    else:
                        word += char
                        entity_type = indexes[i]

            
            
        no_lines += 1

        if len(entities) > 0:
            corpus.append(entities)

        # break

        # if no_lines > 2:
        #     break

    return training_data
    # except Exception as e:
    #     print("Unable to process " + file + "\n" + "error = " + str(e))
    #     return None


convert_file_to_conll("v1.json1")


# the duplicate code, ddn't work well
# pending_lines = []

# with open("file.json", 'r') as f:
#     lines = f.readlines()

#     for line in lines:
#         org_json = json.loads(line)
#         org_text = org_json["text"]

#         found = False
#         with open("annotated-manually-10-dec.json", 'r') as f1:
#             lines1 = f1.readlines()
#             for line1 in lines1:
#                 org_json1 = json.loads(line1)
#                 org_text1 = org_json1["text"]

#                 if org_text == org_text1:
#                     found = True
#                     print("duplicate")
#                     break

#         if not found:
#             pending_lines.append(line)


# open("pending-file.json", 'w').close()
# with open("pending-file.json", 'a') as the_file:
#     for line in pending_lines:
#         the_file.write(line)

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
                the_file.write(ent + "\n")

            the_file.write("\n")

write_lines_file('ner-full.txt', corpus)
write_lines_file('ner-train.txt', train_data)
write_lines_file('ner-test.txt', test_data)
write_lines_file('ner-dev.txt', dev_data)