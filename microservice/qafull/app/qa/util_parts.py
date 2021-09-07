import spacy
import time
from flair.data import Sentence
import copy
from fuzzywuzzy import fuzz
import re
from app.logging import logger
import json
from app.account import initDB
from bson.objectid import ObjectId

import json
from app.qa.util import combine_ner_into_entites


def get_parts_label():
    with open('/workspace/distilbert-resume-parts-classify/label_list.txt') as json_file:
        label_list = json.load(json_file)
        return label_list


tag_list = ["PERSON", "ORG", "Phone", "DOB", "DATE", "Email",
            "EducationDegree", "Designation", "ExperianceYears", "GPE"]

questions_not_tags = {
    "personal_name": {
        "education": ["EducationDegree", "CARDINAL", "ORG", "DATE"],
        "work": ["Designation", "ExperianceYears", "ORG", "DATE"]
    },
    "summary": {
        "education": ["EducationDegree", "CARDINAL", "ORG", "DATE"]
    },
    "total_experiance": {
        "education": ["EducationDegree", "CARDINAL", "ORG", "DATE"]
    },
    "exp_": {
        "education": ["EducationDegree", "CARDINAL", "ORG", "DATE"],
        "personal": ["PERSON", "DOB", "GPE", "Email"]
    },
    "projects_": {
        "education": ["EducationDegree", "CARDINAL", "ORG", "DATE"],
        "personal": ["PERSON", "DOB", "GPE", "Email"]
    },
    "skills":  {
        "education": ["EducationDegree", "CARDINAL", "ORG", "DATE"],
        "personal": ["PERSON", "DOB", "GPE", "Email"]
    },
    "education_": {
        "work": ["Designation", "ExperianceYears", "ORG", "DATE"],
        "personal": ["PERSON", "DOB", "GPE", "Email"]
    },
    "certifications": {},
    "training": {},
    "hobbies": {},
    "awards": {},
    "extra": {},
    "references": {}
}

questions = {
    "personal_name": "what is your name?",
    "summary": "what is your career objective or executive summary",
    "total_experiance": "how much total experience do you have?",
    "exp_company": "which company did you work with most recently?",
    "exp_designation": "what was your most recent designation",
    "exp_duration": "what was your recent job duration?",
    # "exp_res": "what are your recent job responsibilities",
    "projects_name": "what is your most recent project",
    # "projects_skills": "what skillset or technologies you have used in your most recent projects?",
    "skills": "what are your skills or area of expertise?",
    "education_degree": "what is your education qualification",
    "education_year": "when year did you passout?",
    "certifications": "have you done any certifications",
    "training": "have you done any trainings",
    "hobbies": "what are your hobby",
    "personal_location": "where do you live",
    "personal_dob": "what is your date of birth",
    "awards": "any accomplishments or carrier highlights or awards?",
    "extra": "what are your favorite extra curricular activatives",
    "references": "do you have any references"
}

nlp = spacy.load('en_core_web_sm')


def standardize_unicode(line):
    if "\uf0b7" in line:
        line = line.replace("\uf0b7", "\u2022")

    if "\u25cf" in line:
        line = line.replace("\u25cf", "\u2022")

    if "\uf005" in line:
        line = line.replace("\uf005", "\u2022")

    if "\u2019s" in line:  # left side quotation
        line = line.replace("\u2019s", "'")

    if "\uf0a7" in line:  # invalid character
        line = line.replace("\uf0a7", "")

    if "\u2018s" in line:  # right side quotation
        line = line.replace("\u2018s", "'")

    return line


def get_nlp_sentences(row, debug=True):
    # print("=========================section=========================")
    if "type" not in row:
        row["type"] = ""

    if row["type"] == "text":
        sentence = row["sentence"]
        display_text = row["display_text"]
        mini_sentence = []
        new_dispaly_text = []
        for display_row in display_text:
            # if display_row['type'] == "text" or display_row["type"] == "table" or display_row["type"] == "line":
            if not isinstance(display_row["text"], list):
                mini_sentence.append(display_row["text"])
            else:
                mini_sentence.extend(display_row["text"])

        if len(mini_sentence) > 0:
            if len(mini_sentence) == 1:
                mini_sentence[0] = standardize_unicode(mini_sentence[0])
                return mini_sentence
            else:

                if debug:
                    print("mini_sentence", json.dumps(mini_sentence, indent=1))
                doc = nlp(" ".join(mini_sentence))
                all_sents = []
                for sidx, sent in enumerate(doc.sents):
                    sent = " ".join(sent.text.split())
                    # print(f":{sent}")
                    all_sents.append(sent)

                new_sents = []

                tree = {}
                tree_taken_idx = []

                for idx, sent in enumerate(all_sents):
                    tree[sent] = []

                    for idx2, mini_sent in enumerate(mini_sentence):

                        # I was posted in Emergency ward and in ICU during my final year in Vydehi Hospital, Mysuru • Research Methodology • External Monitor in Mission Indardhanush (Govt of Karnataka) xxxx • I was posted in Emergency ward and in ICU during my
                        # this is not matching simply because of an extra . character
                        mini_sent_re = re.sub(r'\W+', '', mini_sent)
                        sent_re = re.sub(r'\W+', '', sent)
                        # print(sent_re, "xxxx", mini_sent_re)
                        if len(mini_sent_re.strip()) > 0 and (mini_sent_re in sent_re or mini_sent_re == sent_re):
                            # print("inside", mini_sent)
                            tree_taken_idx.append(idx2)
                            tree[sent].append(mini_sent)
                            if sent == " ".join(tree[sent]):
                                break
                            # all good
                        else:
                            # this is a problem
                            pass

                tree2 = {}

                for idx, sent in enumerate(mini_sentence):
                    if idx in tree_taken_idx:
                        continue
                    tree2[sent] = []

                    for idx2, mini_sent in enumerate(all_sents):
                        # print(f"mini_sent {mini_sent} sent {sent}")
                        mini_sent_re = re.sub(r'\W+', '', mini_sent)
                        sent_re = re.sub(r'\W+', '', sent)

                        if len(mini_sent_re.strip()) > 0 and (mini_sent_re in sent_re or mini_sent_re == sent_re):
                            tree2[sent].append(mini_sent)
                            if sent == " ".join(tree2[sent]):
                                break
                            # all good
                        else:
                            pass
                if debug:
                    print("tree_taken_idx", tree_taken_idx)
                    print("tree", json.dumps(tree, indent=1))
                    print("tree2", json.dumps(tree2, indent=1))

                sentences_list = []
                for idx, sent in enumerate(tree):
                    sentences_list.append(sent)

                matches_idx = []
                last_idx = -1
                for idx, sent in enumerate(sentences_list):
                    if debug:
                        print("=========================================")
                    for idx2, sent2 in enumerate(tree2):
                        if idx2 < last_idx:
                            continue

                        if len(tree[sent]) == 0:
                            if sent in tree2[sent2]:
                                last_idx = idx2
                                if debug:
                                    print("sent ", sent, "sent2 ", sent2)

                                if sent2.find(sent) == 0:
                                    if debug:
                                        print(sent, "1111", sent2, "idx", idx2)
                                    # there is a problem here. ideally in this case there should be a full match only i.e if sent is inside sent2. then sent2 array should have another parts
                                    # in some cases this doesnt happen. need to see how to handle.
                                    if idx2 not in matches_idx:
                                        matches_idx.append(idx2)
                                        sentences_list[idx] = sent2
                                        if sent != sent2:
                                            # this means there is some extra text in sent2
                                            if len(tree2[sent2]) == 1:
                                                # this means there is some extra text but its not there in array. this is a problem.
                                                # this would ideally mean the next sentence the text. so this results in duplicate text
                                                if idx != len(sentences_list) - 1:
                                                    next_sent = sentences_list[idx + 1]
                                                    if next_sent in sent2:
                                                        sent2 = sent2.replace(
                                                            next_sent, "")
                                                        sentences_list[idx] = sent2
                                    else:
                                        sentences_list[idx] = ""

                                else:
                                    if debug:
                                        print(sent, "2222",
                                              sent2, "idx2", idx2)
                                    if idx != 0 and sent2.split(" ")[0] in sentences_list[idx - 1]:
                                        # ok this first word is present in the sentence. need a better check in this for sure.
                                        if debug:
                                            print("matches_idx", matches_idx)
                                        if idx2 not in matches_idx:
                                            # find the same words
                                            sent1 = sentences_list[idx - 1]

                                            index = 0

                                            try:
                                                rindex = len(sent1.split(" ")) - 1 - sent1.split(" ")[::-1].index(sent2.split(" ")[0])
                                            except ValueError as e:
                                                break
                                            while True:
                                                if rindex+index >= len(sent1.split(" ")):
                                                    break

                                                if debug:
                                                    print(sent1.split(" ")[
                                                          rindex+index], "===",  sent2.split(" ")[index])

                                                if sent1.split(" ")[rindex+index] == sent2.split(" ")[index]:
                                                    index += 1
                                                    continue
                                                else:
                                                    break

                                            sentences_list[idx - 1] = sentences_list[idx -
                                                                                     1] + " " + " ".join(sent2.split(" ")[index:])
                                            if debug:
                                                print(
                                                    "here new sents", sentences_list[idx - 1], "idx2", idx2)
                                            matches_idx.append(idx2)

                                        sentences_list[idx] = ""
                                    else:
                                        print("this should not happen at all!")
                                        pass

                                break

                new_sent_list = []
                for sent in sentences_list:
                    sent = standardize_unicode(sent)

                    unicode_chars = ["\u2022"]
                    for uni in unicode_chars:
                        if uni in sent:
                            if sent.count(uni) > 2:
                                # if multiple dots it might be part of the same sentence only
                                new_sent_list.append(sent)
                            else:
                                if sent.rindex(uni) == 0:
                                    new_sent_list.append(sent)
                                else:
                                    new_sent_list.extend([
                                        sent[:sent.rindex(uni)],
                                        uni + sent[sent.rindex(uni)+1:]
                                    ])
                            break
                    else:
                        new_sent_list.append(sent)

                new_sent_list = list(filter(None, new_sent_list))

                # if debug:
                print("sentences_list ", json.dumps(new_sent_list, indent=1))
                return new_sent_list


allowed_classification = {
    "summary": ["summary", "skills"],
    "hobbies": ["hobbies", "personal"],
    "projects_": ["projects_", "skills", "exp_", "certifications"],
    "skills": ["skills", "projects_"],
    "personal_": ["personal_", "references", "hobbies"],
    "references": ["references", "personal"],
    "exp_": ["exp_", "projects_", "skills", "summary", "certifications"],
    "education_": ["education_"],
    "training": ["traning", "exp_", "projects_", "skills", "summary", "certifications"],
    "awards": ["awards", "certifications"],
    "certifications": ["certifications", "awards"],
    "extra": ["extra"]
}


def get_new_section_map(final_section_ui_map, classifier):
    new_section_map = {}
    label_list = get_parts_label()
    for idx in final_section_ui_map:
        print("idx", idx)
        qa_parse_resume = final_section_ui_map[idx]
        different_sections = {}
        new_sections = {}

        for key in qa_parse_resume:
            print(">>>>>>>>>> ", key)
            unmatched_section = []
            new_sections[key] = []
            for line in qa_parse_resume[key]:
                if "type" not in line:
                    if key not in questions:
                        unmatched_section.append(line)
                    else:
                        new_sections[key].append(line)

                    continue

                if line["type"] == "heading" or line["type"] == "heading_alternate" or line["type"] == "title":
                    if key not in questions:
                        unmatched_section.append(line)
                    else:
                        new_sections[key].append(line)

                    continue

                score_thresh = .85

                primary_label = key

                new_key = None
                if key not in questions:
                    sentence = " ".join(line["sentence"])
                    print("full sentence", sentence)
                    if len(sentence) > 512:
                        sentence = sentence[:512]
                    out = classifier(sentence)
                    label_id = int(out[0]["label"].replace("LABEL_", ""))
                    score = out[0]["score"]
                    if score > score_thresh:
                        primary_label = label_list[label_id]
                        print(label_list[label_id],
                              ">>>>>>>>>>>>", out[0]["score"])
                        print("")
                        print("++++++++++++++++++++")
                        print("")
                    else:
                        primary_label = key
                        if '_' in primary_label:
                            primary_label = primary_label.split("_")[0] + "_"
                        else:
                            found = False
                            for qk in questions.keys():
                                if qk in primary_label:
                                    primary_label = qk
                                    found = True
                                    break

                            if not found:
                                print(primary_label)
                                assert(False)

                    if primary_label not in different_sections:
                        different_sections[primary_label] = []

                    new_key = primary_label + "_" + key
                    if new_key not in different_sections:
                        different_sections[new_key] = []

                    different_sections[new_key].extend(unmatched_section)
                    unmatched_section = []

                else:
                    if '_' in primary_label:
                        primary_label = primary_label.split("_")[0] + "_"

                print("display text +++++++++++++++++++++++++++++++")
                new_sent_list = get_nlp_sentences(line, False)

                print("++++++++++++++++++++")

                # here will will group sentences based based on label classifier
                # doc = nlp(sentence)
                if new_sent_list:
                    previous_label = None
                    previous_score = None
                    current_label = ""
                    current_score = 0
                    label_match_sent_list = []
                    for sentence in new_sent_list:
                        # sentence = sent.text
                        is_previous = False
                        if len(sentence.split(" ")) > 1:
                            if len(sentence) > 512:
                                sentence = sentence[:512]
                            out = classifier(sentence)
                            label_id = int(
                                out[0]["label"].replace("LABEL_", ""))
                            label = label_list[label_id]
                            score = out[0]["score"]
                            if score > score_thresh:
                                current_label = label
                                current_score = previous_score
                            else:
                                if previous_label:
                                    current_label = previous_label
                                    current_score = previous_score
                        else:
                            print("previous >>>> ",
                                  previous_label, "::", sentence)
                            if previous_label:
                                current_label = previous_label
                                current_score = previous_score
                                is_previous = True

                        if current_label != "" and primary_label in allowed_classification and current_label not in allowed_classification[primary_label]:
                            # this is a problem
                            if current_label not in different_sections:
                                different_sections[current_label] = []

                            different_sections[current_label].append({
                                "sentence": sentence,
                                "label": current_label,
                                "score": current_score,
                                "is_previous": is_previous,
                                "org_label": primary_label

                            })
                            print("#moving#", current_label, score, "#from",
                                  primary_label, ">>>>>>>>>>>>", sentence)
                        else:
                            label_match_sent_list.append({
                                "sentence": sentence,
                                "label": current_label,
                                "score": current_score,
                                "is_previous": is_previous
                            })
                            print(current_label, current_score,
                                  ">>>>>>>>>>>>", sentence)

                        previous_label = current_label
                        previous_score = current_score

                    if len(label_match_sent_list) > 0:
                        if key not in questions:
                            different_sections[new_key].append(
                                label_match_sent_list)
                        else:
                            new_sections[key].append(label_match_sent_list)

        print("*************************")
        print("")
        print("")
        print("")
        print("new sections")
        print(json.dumps(new_sections, indent=1))
        print("different sections")
        print(json.dumps(different_sections, indent=1))
        new_section_map[idx] = {
            "new_sections": new_sections,
            "different_sections": different_sections
        }
        return new_section_map



def combine_new_section_map(new_section_map):
    final_combine = {}
    for idx in new_section_map:
        final_combine[idx] = {}
        new_sections = new_section_map[idx]["new_sections"]
        different_sections = new_section_map[idx]["different_sections"]
        for section_key in new_sections:
            final_combine[idx][section_key] = []
            sentences = []
            display_text = []
            for line in new_sections[section_key]:
                if isinstance(line, dict):
                    final_combine[idx][section_key].append(line)
                else:
                    for sub_line in line:
                        sent = sub_line["sentence"]
                        sentences.append(sent)
                        display_text.append({
                            'type': "text",
                            "text": sent
                        })

            if len(sentences) > 0:
                final_combine[idx][section_key].append({
                    "type": 'text',
                    "sentence": sentences,
                    "display_text": display_text
                })

        for section_key in different_sections:
            if section_key not in final_combine[idx]:
                final_combine[idx][section_key] = []

            sentences = []
            display_text = []
            for line in different_sections[section_key]:
                if isinstance(line, dict):
                    if "text" in line:
                        sentences.append(line["text"])
                        display_text.append({
                            'type': "text",
                            "text": line["text"]
                        })
                    else:
                        sentences.append(line["sentence"])
                        display_text.append({
                            'type': "text",
                            "text": line["sentence"]
                        })

                else:
                    for sub_line in line:
                        sent = sub_line["sentence"]
                        sentences.append(sent)
                        display_text.append({
                            'type': "text",
                            "text": sent
                        })

            if len(sentences) > 0:
                final_combine[idx][section_key].append({
                    "type": 'text',
                    "sentence": sentences,
                    "display_text": display_text
                })

        print(json.dumps(final_combine, indent=1))

    return final_combine




def get_tags_subsections_subanswers(complete_section_match_map, tagger):
    section_ui_map = {}
    for idx in complete_section_match_map:
        print("idx: ", idx)
        complete_section_match_idx = complete_section_match_map[idx]

        for question_key in complete_section_match_idx.keys():
            print("question_key ", question_key)
            lines = []
            for idx2, ui in enumerate(complete_section_match_idx[question_key]):

                # if ui['type'] == "title" or  ui['type'] == "heading" or  ui['type'] == "heading_alternate":
                #   continue

                if "text" in ui:
                    lines.append(ui['text'])
                else:
                    lines.append(" ".join(ui['sentence']))

            print(lines)
            print("_____")

            if len(lines) == 0:
                continue

            print("************extracting tags************")
            complete_section_match_idx[question_key][idx2]["tags"] = []
            for line in lines:
                start_time = time.time()
                # print(f"ner line: {line}")
                # if len(line) < 512:
                line = re.sub(' +', ' ', line)
                sentence = Sentence(
                    line, use_tokenizer=False)  # this for email
                tagger.predict(sentence)
                # else:
                #   sentence = Sentence(line[:512], use_tokenizer= False)
                #   tagger.predict(sentence)

                urls = re.findall(
                    "https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+", line)
                if urls:

                    print("found urls:")
                    # in this spaces are coming 5f70cfe80f22e9003956efe4
                    # print(line)
                    print(urls)
                    complete_section_match_idx[question_key][idx2]["urls"] = urls

                tag_dict = sentence.to_dict(tag_type='ner')
                # for entity in sentence.get_spans('ner'):
                # print(entity)
                # print(json.dumps(tag_dict, indent=1, default=str))
                # print(tag_dict)
                custom_entities, new_tag_dict = combine_ner_into_entites(
                    tag_dict)
                complete_section_match_idx[question_key][idx2]["tags"].extend(
                    custom_entities)
                # print(json.dumps(custom_entities, indent=1))
                # print("time taken for answer :" , time.time() - start_time )
                print("----------------------------------")
                # process.exit(0)

            # if len(line.split(" ")) > 10 and False: #atleast 10 words to ask any questions else no use. disabling it
            #   complete_section_match_idx[question_key][idx2]["questions"] = []
            #   for question_key in sub_question_to_ask:
            #     for sub_ques_key in sub_question_to_ask[question_key]:
            #       sub_question = sub_question_to_ask[question_key][sub_ques_key]

            #       print("****** asking question *********")
            #       print(sub_question)

            #       start_time = time.time()
            #       try:
            #         if len(line) > 2048:
            #           new_line = line[:2048]
            #         else:
            #           new_line = line

            #         answer = question_answerer({
            #           'question': sub_question,
            #           'context': new_line
            #         }, handle_impossible_answer = True)
            #         print(answer)
            #         answer['question'] = sub_question
            #         complete_section_match_idx[question_key][idx2]["questions"].append(answer)
            #         print("time taken for answer :" , time.time() - start_time )
            #         print("context length: ", len(line))

            #       except Exception as e:
            #         pass

        complete_section_match_map[idx] = complete_section_match_idx

    return complete_section_match_map

