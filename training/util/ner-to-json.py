import jsonlines
import json


def convert_ner_to_json(filename):
    result = []
    with open(filename, 'r') as f:
        data = f.readlines()
        print("no of lines", len(data))
        for row in data:
            if isinstance(row, str) and len(row.strip()) == 0:
                result.append(("", ""))
            else:
                row = row.split(" ")
                result.append((row[0].strip(), row[-1].strip()))

    print("total lines", len(result))

    lines = []

    isTagFound = False
    tagText = []
    tagName = ""
    words = []
    tags = []
    tag_start_index = -1
    counter = 0

    for (word, tag) in result:
        if isinstance(word, str) and len(word.strip()) == 0:
            # new line
            if len(tagText) > 0:
                tags.append({tagName:  " ".join(
                    tagText), "start_idx": tag_start_index, "tag": tagName, "text": " ".join(tagText)})
                tagName = ""
                tagText = []
                isTagFound = False
                tag_start_index = -1


            counter = 0

            lines.append({
                "line": " ".join(words),
                "tags": tags
            })
            words = []
            tags = []
            continue

        counter += len(word) + 1  # 1 for space
        words.append(word)

        if isTagFound and tag != tagName:
            # tag completed
            # print("tag found ", " ".join(tagText), " ", tagName)
            # see if there is any substitute for it
            tags.append({
                tagName:  " ".join(tagText), 
                "start_idx": tag_start_index,
                "tag": tagName, 
                "text": " ".join(tagText)
            })

            

            tag_start_index = -1

            tagName = ""
            tagText = []
            isTagFound = False

        if tag != "O":
            if tag_start_index == -1:
                tag_start_index = counter - len(word) - 1
            isTagFound = True
            tagText.append(word)
            tagName = tag

    with open(filename.replace(".txt", ".json"), 'w') as f:
        writer = jsonlines.Writer(f)
        writer.write_all(lines)

    return lines


TAGS = {
    'LANGUAGE': "Which langauge does he speak",
    'Email': "whats his email address",
    'GPE': "what his location ",
    'EducationDegree': "what is his education degree",
    'Designation': "what his designation",
    'PERSON': "what his name",
    'ExperianceYears': "what his experiance",
    'ORG': "what his organization",
    'CARDINAL': "what his score",
    'DATE': "what the date",
    'DOB': "what the date of birth",
    'Phone': "what his phone no"
}


def convert_lines_to_qa(lines, filename):

    final_list = []

    len_of_context = 0
    total_no_context = 0

    to_file = {
        "version": "0.0.1",
        "data": [
            
        ]
    }

    for idx, line in enumerate(lines):
        # print(line)

        format = {
            "title": "",
            "paragraphs": []
        }

        qa = {}
        context = line["line"]
        qa["context"] = context
        qa["qas"] = []

        len_context = len(context)

        len_of_context += len_context
        total_no_context += 1
        
        
        for TAG in TAGS.keys():
            question = TAGS[TAG]
            tag_found = False

            for t in line["tags"]:
                tagname = t["tag"]
                if TAG == tagname:
                    text = t["text"]
                    start_idx = t["start_idx"]

                    qa["qas"].append({
                        "question": question,
                        "id": idx,
                        "answers": [
                            {
                                "answer_start": start_idx,
                                "text": text
                            }
                        ],
                        "is_impossible": False
                    })
                    tag_found = True
                    if (len(text) + start_idx  > len_context ):
                        print("there is some issue")
                        print(line)

            if(not tag_found):
                qa["qas"].append({
                    "question": question,
                    "id": idx,
                    "answers": [],
                    "is_impossible": True
                })

        format["paragraphs"].append(qa)
        to_file['data'].append(format)
        # break

    # print(final_list)
    with open(filename.replace(".txt", "_mrc.json"), 'w') as outfile:
        json.dump(to_file, outfile)


    print("avg context length ", (len_of_context/total_no_context))
    return final_list


filename = "label_remove_ner-final-train.txt"
lines = convert_ner_to_json(filename)
convert_lines_to_qa(lines, filename)


filename = "label_remove_ner-final-test.txt"
lines = convert_ner_to_json(filename)
convert_lines_to_qa(lines, filename)

filename = "label_remove_ner-final-dev.txt"
lines = convert_ner_to_json(filename)
convert_lines_to_qa(lines, filename)