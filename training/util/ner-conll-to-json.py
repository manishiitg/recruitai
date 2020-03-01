import json
import uuid


def convert_conll_to_label_studio_nerfile(file):
    # try:
    result = []
    with open(file, "r") as myfile:
        nerTestLines = myfile.read()
        nerTestLines = nerTestLines.splitlines()

        for line in nerTestLines:
            if len(line.strip()) == 0:
                result.append(("", ""))
                continue

            result.append(
                (line.split("  ")[0].strip(), line.split("  ")[1].strip()))

    lines = []

    isTagFound = False
    tagText = []
    tagName = ""
    words = []
    tags = []
    # this is when assumention thet there are two lines i.e 2 lines spaces between cv data
    # and single line data between actua llines

    has_two_lines = True
    count_empty_line = 0

    for (word, tag) in result:
        if isinstance(word, str) and len(word.strip()) == 0:
            count_empty_line += 1

            # new line
            if len(tagText) > 0:
                tags.append({
                    "tagName": tagName,
                    "text":  " ".join(tagText)
                })
                tagName = ""
                tagText = []
                isTagFound = False

            
            
            if has_two_lines:
                if count_empty_line == 1:
                    word = "\n"
                    tag = "O"

                if count_empty_line == 2:
                    lines.append({
                        "line": " ".join(words),
                        "tags": tags
                    })
                    words = []
                    tags = []
                    continue
            else:
                lines.append({
                    "line": " ".join(words),
                    "tags": tags
                })
                words = []
                tags = []
                continue
                

            

        else:
            count_empty_line = 0


        if tag == "Skills":
            tag = "O"

        words.append(word)

        if isTagFound and tag != tagName:
            # tag completed
            # print("tag found ", " ".join(tagText), " ", tagName)
            # see if there is any substitute for it
            tags.append({
                "tagName": tagName,
                "text":  " ".join(tagText)
            })

            tagName = ""
            tagText = []
            isTagFound = False

        if tag != "O":
            isTagFound = True
            tagText.append(word)
            tagName = tag

    final_json = {}

    for line in lines:
        tags = line["tags"]
        line = line["line"]
        lineIndex = 0
        result = []
        for tag in tags:
            res = {
                "from_name": "ner",
                "honeypot": True,
                "id": uuid.uuid4().hex,
                "source": "$text",
                "to_name": "text",
                "type": "labels",
                "value": {
                    "start": line.index(tag["text"], lineIndex),
                    "end": line.index(tag["text"], lineIndex) + len(tag["text"]),
                    "labels": [
                        tag["tagName"]
                    ],
                    "text": tag["text"]
                }
            }
            lineIndex += len(tag["text"])
            result.append(res)

        completion = {
            "completions": [{
                "id": uuid.uuid4().hex,
                "lead_time": 20,
                "result": result,
                "data" : {
                    "text": line
                },
                "id": len(final_json),
                "task_path": "../tasks.json"
            }]
        }
        data = json.dumps(completion, indent=1)
        with open('ner/completions/' + str(len(final_json)) + '.json', 'w') as f:
            f.write(data)

        obj = {
            "data" : {
                "text": line,
                "id": len(final_json)
            }

        }
        final_json[str(len(final_json))] = obj
        

    return final_json


from pathlib import Path
Path("../../label-studio/ner/completions").mkdir(parents=True, exist_ok=True)

final_json = convert_conll_to_label_studio_nerfile("ner-full.txt")

data = json.dumps(final_json, indent=1)
with open('../../label-studio/ner/tasks.json', 'w') as f:
    f.write(data)
