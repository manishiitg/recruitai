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

    for (word, tag) in result:
        if isinstance(word, str) and len(word.strip()) == 0:
            # new line
            if len(tagText) > 0:
                tags.append({
                    "tagName": tagName,
                    "text":  " ".join(tagText)
                })
                tagName = ""
                tagText = []
                isTagFound = False

            lines.append({
                "line": " ".join(words),
                "tags": tags
            })
            words = []
            tags = []
            continue

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

    final_json = []

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
                    "start": line.index(tag["text"] , lineIndex),
                    "end": line.index(tag["text"]  , lineIndex) + len(tag["text"]),
                    "labels": [
                        tag["tagName"]
                    ],
                    "text": tag["text"]
                }
            }
            lineIndex += len(tag["text"])
            result.append(res)

        obj = {
            "completions": [{
                "id": 1,
                "lead_time": 20,
                "result": result
            }], 
            "data": {
                "text": line
            },
            "id": len(final_json)
        }
        final_json.append(obj)

    return final_json


final_json = convert_conll_to_label_studio_nerfile("ner-v1-full.txt")

import json
with open('ner-label-studio.json', 'w') as f:
    json.dump(final_json, f)