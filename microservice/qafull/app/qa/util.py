import time
from flair.data import Sentence
import copy
from fuzzywuzzy import fuzz
import re
from app.logging import logger
import json

def clean_page_content_map(idx, page_contents):

    page_content_map = {}

    content = "\n".join(page_contents).replace(
        "\n\n\n", "").replace(u'\xa0', u' ')

    xlines = content.splitlines()

    new_lines = []
    empty_lines = 0
    for line in xlines:
        if len(line.strip()) == 0:
            empty_lines += 1
        else:
            empty_lines = 0

        if empty_lines >= 3:
            continue

        new_lines.append(line)

    cleanLineData = []
    for line in new_lines:
        # line = re.sub('\s+', ' ', line).strip() # this is giving warning on server
        # line = ' '.join(line.split())
        new_words = []
        for word in line.split(" "):
            if word.find("(cid:") >= 0 and word.find(")") >= 0:
                pass
            else:
                new_words.append(word)

        line = " ".join(new_words)

        len_words = 0
        for word in list(filter(None, line.split(' '))):
            if len(word) > len_words:
                len_words = len(word)

        if len_words == 1 and len(list(filter(None, line.split(' ')))) > 2:
            # logger.info("some issue with line %s", line)
            line = "".join(line.split(" "))
            # logger.info("new line %s", line)

        cleanLineData.append(line)

    line_without_space = 0
    for line in cleanLineData:
        if " " not in line.strip() and len(line) > 10:  # if more than 10 its not a single word
            line_without_space += 1
        else:
            words = line.split(" ")
            if len(words) == 2:
                line_without_space += 1

    if (line_without_space > len(cleanLineData) / 2) and len(cleanLineData) > 10:
        logger.info("line issue skipping")
        # logger.info(content)
        return None

    page_content_map[idx] = "\n".join(cleanLineData)

    return page_content_map


def get_page_and_box_map(bbox_map):
    bbox_map_int = {}
    page_box_count = {}
    for idx in bbox_map:
        bbox_list = bbox_map[idx]
        # logger.info(f"idx {idx}")
        page_box_count[idx] = {}
        bbox_map_int[idx] = {}
        for page in bbox_list:
            bbox_map_int[idx][int(page)] = []
            if len(bbox_list[page]) > 0:
                page_box_count[idx][int(page)] = len(
                    bbox_list[page])  # just get max box id of a page
            for box_id, bbox in enumerate(bbox_list[page]):
                bbox_map_int[idx][int(page)].append(bbox)

    return bbox_map_int, page_box_count


def get_section_match_map(answer_map, bbox_map_int, page_box_count, page_content_map):
    section_match_map = {}

    for i, idx in enumerate(answer_map):
        question_answers = answer_map[idx]
        bbox_list = bbox_map_int[idx]
        logger.info(f"idx {idx}")

        # this array will contain which questions answer matched which line sections
        section_match_idx = []
        for ques_idx, question_key in enumerate(question_answers):
            answer = question_answers[question_key]
            if "error" in answer:
                continue
            if len(answer['answer']) == 0:
                logger.info("skipping %s answer %s",
                            answer['question'], answer["answer"])
                continue

            logger.info(
                f"checking {answer['question']} question key {answer['question_key']}")
            answer_found_in_boxes = False
            found_single_match = False

            line_idx = 0

            inner_section_match_idx = []
            for page in bbox_list:
                for box_id, bbox in enumerate(bbox_list[page]):
                    # bbox = bbox_list[page][box_idx]
                    # logger.info(bbox.keys())

                    line = bbox["line"].strip()
                    line_start_idx = line_idx
                    line_idx += len(bbox["line"])
                    answer_text = answer["answer"].strip()
                    if len(line) > 0:
                        start_idx = answer["start"]
                        end_idx = answer["end"]

                        # logger.info(f"answer {answer_text}  line {line}")
                        if answer_text.lower() in line.lower():
                            logger.info(
                                f"idx {page}-{box_id} question :{answer['question_key']}: answer {answer_text} found in line {line}")
                            # found_single_match = True
                            logger.info(
                                f"idxs' line_start_idx : {line_start_idx} line_end_idx :{line_idx}  start_idx :{start_idx}  end_idx :{end_idx}")
                            # if start_idx > (line_start_idx - 20) and end_idx < (line_idx + 20):
                # need to match based on index and not just the first string:
                # taking padding of 20 characters on both sides for spaces etc
                            answer_found_in_boxes = True
                # logger.info("matched")
                            inner_section_match_idx.append({
                                "page": page,
                                "box_id": box_id,
                                "question_key": answer['question_key'],
                                "score": answer["score"],
                                "ques_idx": ques_idx,
                                "start_idx": start_idx,
                                "end_idx": end_idx,
                                "line_start_idx": line_start_idx,
                                "line_idx": line_idx,
                                "dist": abs(start_idx - line_start_idx)
                            })

                        else:
                            # logger.info(bbox)
                            pass

            # if found_single_match and not answer_found_in_boxes:
            #   assert(False)
            if answer_found_in_boxes:
                if len(inner_section_match_idx) > 1:
                    # need to best match based on idx
                    best_match = None
                    best_match_dist = 99999999
                    for x_match in inner_section_match_idx:
                        logger.info(x_match)
                        dist = x_match["dist"]
                        if dist < best_match_dist:
                            best_match_dist = dist
                            best_match = x_match

                    logger.info(f"best match {best_match}")
                    section_match_idx.append(best_match)
                else:
                    section_match_idx.extend(inner_section_match_idx)

            if not answer_found_in_boxes:

                reverse_answer_found = False
                lines = []

                logger.info(
                    f"          anwser not found :{answer['question']}: with answer :{answer['answer']}: need to debug")

                # should have consicutive matches here. this happens for skills etc where we have skills in multiples lines
                # then muliple line matches the skills.

                line_match_count = 0
                line_match_index = []
                is_one_sentence_match_fine = False

                for page in bbox_list:
                    if reverse_answer_found:
                        break
                    for box_id, bbox in enumerate(bbox_list[page]):
                        # logger.info(f"{page}-{box_id} === {bbox['line']}")
                        line = bbox["line"].strip().lower()
                        lines.append(line)
                        answer_text = answer['answer'].strip().lower()

                        logger.info(f":::::::::::::::::: {line}")
                        line = " ".join([re.sub('[\W\_]', '', word)
                                         for word in line.split(" ")]).strip()
                        if len(line) > 0:
                            # reverse match makes sense only when line is smaller that answer. this means answer is across multiple lines

                            answer_text = " ".join(
                                [re.sub('[\W\_]', '', word) for word in answer_text.split(" ")])

                            ratio = fuzz.partial_ratio(line, answer_text)
                            logger.info(
                                f"---- ratio {ratio} for :{answer_text}: line :{line}:  page :{page} box_id :{box_id}")
                            if len(line) < len(answer_text):
                                if ratio > 95:
                                    is_one_sentence_match_fine = True
                                if line in answer_text or ratio >= 80:
                                    line_match_count += 1
                                    logger.info(
                                        f"...............reverse match found #{line}# in #{answer_text}#  line match count {line_match_count}")
                                    line_match_index.append(
                                        {"page": page, "box_id": box_id, "question_key": answer['question_key'], "score": answer["score"], "ques_idx": ques_idx})
                                else:
                                    if line_match_count >= 2 or is_one_sentence_match_fine:
                                        logger.info(
                                            f"found conscicutive matches so its good {len(line_match_index)}")
                                        reverse_answer_found = True
                                        # section_match_idx.extend(line_match_index)
                                        # this is matching multiple sections i am not sure why i added this logic
                                        # it should be on section only
                                        # if having multiple sections then it show for e.g multipe skills in final which is not of any use
                                        section_match_idx.append(
                                            line_match_index[0])
                                        break

                                    elif line_match_count == 1:
                                        logger.info(
                                            "not found consituve matches its bad")
                                        line_match_index = []
                                        # assert(False) # debug this

                                    line_match_count = 0

                # break
                if not reverse_answer_found:
                    logger.info(
                        f"every reverse match not found================z")
                    # case here was experiance matched as 4.5 years but in prediction match 4.5 was not there at all it was just year..
                    # so in this case need to match futher words. of the match and get a best match. not exact match
                    start_idx = answer["start"]
                    end_idx = answer["end"]

                    page_content = page_content_map[idx]

                    incr_idx = end_idx + 1
                    max_words = 3
                    max_chars = 30
                    count_words = len(answer['answer'].split(" "))
                    count_chars = len(answer['answer'])
                    while True:
                        if incr_idx > len(page_content) - 1:
                            break

                        char = page_content[incr_idx]
                        incr_idx += 1
                        if char == " " or char == "\n":
                            count_words += 1

                        count_chars += 1
                        if count_chars >= max_chars:
                            break

                        if count_words >= max_words:
                            break

                    padded_sentence = page_content[start_idx:incr_idx]
                    padded_sentence = " ".join(
                        [re.sub('[\W\_]', '', word) for word in padded_sentence.split(" ")])
                    logger.info(
                        f"padded sentence for :{answer['answer']}:  is := {padded_sentence} count chars {count_chars} max words {max_words} answer start {answer['start']}")

                    found = False
                    start_idx = answer["start"]
                    end_idx = answer["end"]
                    line_start_idx = 0

                    # basically we will look for text near by the start_idx only.
                    line_padding = 200
                    # we will not look everywhere in the entire resume lines this can cause issues
                    # this is causing a problem. in very large cv's there are lines which are more than 200 chareters long and due to that those lines get skipped
                    # even if answer is present in that specific
                    # line_end_idx becomes greater than end_idx + 200 if line is very long
                    # so fixing that below in lines 218
                    logger.info(
                        f"start_idx: {start_idx}  end_idx :{end_idx} line_padding :{line_padding}")

                    inner_section_match_idx = []

                    max_match_ratio = 10
                    max_match_row = None
                    for page in bbox_list:
                        for box_id, bbox in enumerate(bbox_list[page]):

                            line = bbox["line"].strip()
                            line = " ".join([re.sub('[\W\_]', '', word)
                                             for word in line.split(" ")]).strip()
                            line_end_idx = line_start_idx + len(bbox["line"])
                            if len(line) == 0:
                                line_start_idx = line_end_idx
                                continue

                            if len(line) > line_padding:
                                line_padding = len(line)

                            if (line_start_idx > (start_idx - line_padding)) and (line_end_idx < (end_idx + line_padding)):

                                padded_sentence_len = len(padded_sentence)
                                sentence_len = len(line)

                                len_diff = abs(
                                    sentence_len - padded_sentence_len)

                                len_diff_percentage = (len_diff / sentence_len)
                                if len_diff_percentage < .2:
                                    ratio = fuzz.ratio(padded_sentence, line)
                                else:
                                    if padded_sentence_len > sentence_len:
                                        ratio = 0
                                    else:
                                        ratio = fuzz.partial_ratio(
                                            padded_sentence, line)

                                logger.info(
                                    f"##### ratio {ratio} for line {line}   start idx {line_start_idx}")
                                if ratio > max_match_ratio:
                                    max_match_ratio = ratio
                                    max_match_row = {"low_ratio_match": True, "page": page, "box_id": box_id, "question_key": answer[
                                        'question_key'], "score": answer["score"], "ques_idx": ques_idx, "ratio": ratio}

                                if ratio >= 80:
                                    # this is wrong. basically this valid only len of line is greated than len of paddded_sentence
                                    # else this will match things like "the" "php" i.e even single words give high match and wrong things gets matched

                                    # also another problem is sometimes, the paddence sentnce is divided into multiple lines
                                    # so its gets mached across consicute lines.

                                    # need to add logic to handle these both cases
                                    logger.info(
                                        f"ratio {ratio} for line {line}")
                                    dist = abs(line_start_idx - start_idx)
                                    inner_section_match_idx.append(
                                        {"page": page, "box_id": box_id, "question_key": answer['question_key'], "score": answer["score"], "ques_idx": ques_idx, "ratio": ratio, "dist": dist})
                                    found = True
                            else:
                                logger.info(
                                    f"skipping line {line} start idx {line_start_idx}  >  (start_idx - line_padding) : {(start_idx - line_padding)} and line_end_idx: {line_end_idx} < (end_idx + line_padding) {(end_idx + line_padding)}")
                                line_start_idx = line_end_idx
                                continue

                            line_start_idx = line_end_idx

                    if len(inner_section_match_idx) > 1:
                        min_dist = 999
                        best_match = None

                        for match in inner_section_match_idx:
                            if match["dist"] < min_dist:
                                min_dist = match['dist']
                                best_match = match

                        if best_match:
                            section_match_idx.append(best_match)

                    elif len(inner_section_match_idx) == 1:
                        section_match_idx.append(inner_section_match_idx[0])

                    if not found:
                        # assert(False)
                        if max_match_row:
                            section_match_idx.append(max_match_row)
                        # not sure what to something detector and resume don't match at all. and this happen rarely.
                        # i guess can simply just take the highest match
                        # pass

        section_match_map[idx] = section_match_idx

    return section_match_map

# hhmm its possible here that two questions got answered in the same sections need to resolve that conflict based on score


def get_resolved_section_match_map(section_match_map):
    new_section_match_map = {}
    for idx in section_match_map:
        section_match_idx = section_match_map[idx]
        new_section_match_idx = []
        to_skip = []
        for i, section in enumerate(section_match_idx):
            page = section["page"]
            box_id = section["box_id"]
            question_key = section["question_key"]
            if i in to_skip:
                logger.info(f"skipped {i}")
                continue

            final_after_confict = section
            for j, section2 in enumerate(section_match_idx):
                if j > i:
                    page2 = section2["page"]
                    box_id2 = section2["box_id"]
                    question_key2 = section2["question_key"]

                    if page == page2 and box_id == box_id2:

                        if question_key.split("_")[0] == question_key2.split("_")[0]:
                            continue

                        # now a new problem came. in one candidate resume. name was getting repeated in many places and it was getting conflicted
                        # again and again. even if questions are not sub subsections its getting conflicted.
                        # confict! 3  question key1: personal_name key2 education_degree
                        # confict! 4  question key1: personal_name key2 education_year
                        # confict! 6  question key1: personal_name key2 personal_location
                        # this is a problem. in this we skipped lot of important information
                        # so for now adding back the logic of checking if key is same for sub question

                        logger.info(
                            f"confict! {j}  question key1: {section['question_key']} key2 {section2['question_key']} ")
                        if section2["score"] > section["score"]:
                            final_after_confict = section2
                            final_after_confict["conflicted_answer"] = section
                        else:
                            final_after_confict["conflicted_answer"] = section2

                        to_skip.append(j)
                        break

            new_section_match_idx.append(final_after_confict)

        def custom(item):
            return item["page"] * 100 + item["box_id"]

        new_section_match_idx = sorted(new_section_match_idx, key=custom)
        new_section_match_map[idx] = new_section_match_idx

    return new_section_match_map


def util_match_row(matched_box, page, box_id, question_key, ques_idx):
    matchedRow = matched_box["matchedRow"]
    section_title = ""
    section_content = []
    absorbed_section_boxes = []

    if "Title" in matchedRow["bucketurl"]:
        # section_title = matchedRow["correctLine"] # we should not use correctLine as that is line from ocr only
        section_title = matched_box["line"]

        if "sortLines" in matched_box:
            ap_sortLines = matched_box["sortLines"]
            ap_list = list(ap_sortLines.values())
            new_ap_list = []
            for l in ap_list:
                if section_title in l:
                    l = l.replace(section_title, "").strip()
                    if len(l) > 0:
                        new_ap_list.append(l)
                else:
                    new_ap_list.append(l)

            section_content.append({
                "type": "list",
                "content": new_ap_list,
                "page": page,
                "box_id": box_id
            })

        else:
            if 'line' in matchedRow:
                if len(matchedRow["line"].strip()) > 0:
                    line = matchedRow["line"].strip()

                    if section_title in line:
                        line = line.replace(section_title, "").strip()

                    section_content.append({
                        "type": "text",
                        "content": line,
                        "page": page,
                        "box_id": box_id
                    })

        absorbed_section_boxes.append(
            {"page": page, "box_id": box_id,
                "question_key": question_key, "ques_idx": ques_idx}
        )
    elif "List" in matchedRow["bucketurl"]:
        if "sortLines" in matched_box:
            ap_sortLines = matched_box["sortLines"]
            ap_list = list(ap_sortLines.values())
        else:
            ap_list = matched_box["matchedRow"]["correctLine"]

        section_content.append({
            "type": "list",
            "content": ap_list,
            "page": page,
            "box_id": box_id
        })
        absorbed_section_boxes.append(
            {"page": page, "box_id": box_id,
                "question_key": question_key, "ques_idx": ques_idx}
        )

    elif "Text" in matchedRow["bucketurl"]:
        ap_line = matchedRow["correctLine"]
        sortLines = []
        if "sortLines" in matched_box:
            sortLines = matched_box["sortLines"]
        section_content.append({
            "type": "text",
            "content": ap_line,
            "sortlines": sortLines,
            "page": page,
            "box_id": box_id
        })
        absorbed_section_boxes.append(
            {"page": page, "box_id": box_id,
                "question_key": question_key, "ques_idx": ques_idx}
        )
    elif "Table" in matchedRow["bucketurl"]:
        ap_line = matchedRow["correctLine"]
        section_content.append({
            "type": "table",
            "content": ap_line,
            "page": page,
            "box_id": box_id
        })
        absorbed_section_boxes.append(
            {"page": page, "box_id": box_id,
                "question_key": question_key, "ques_idx": ques_idx}
        )
    else:
        logger.info(f"look at this {matchedRow['bucketurl']}")
        # assert(False)
        raise Exception(f"look at this {matchedRow['bucketurl']}")

    if "append" in matched_box:
        append = matched_box["append"]
        for appen in append:
            ap_type = appen["type"]
            ap_matchedRow = appen['row']["matchedRow"]
            if "List" in ap_matchedRow["bucketurl"]:
                if "sortLines" in appen["row"]:
                    ap_sortLines = appen["row"]["sortLines"]
                    ap_list = list(ap_sortLines.values())
                else:
                    ap_list = appen["row"]["matchedRow"]["correctLine"]
                section_content.append({
                    "type": "list",
                    "content": ap_list,
                    "ap_type": ap_type,
                    "page": page,
                    "box_id": box_id
                })
                absorbed_section_boxes.append(
                    {"page": page, "box_id": box_id,
                        "question_key": question_key, "ques_idx": ques_idx}
                )

            elif "Text" in ap_matchedRow["bucketurl"]:
                ap_line = ap_matchedRow["correctLine"]
                section_content.append({
                    "type": "text",
                    "content": ap_line,
                    "ap_type": ap_type,
                    "page": page,
                    "box_id": box_id
                })
                absorbed_section_boxes.append(
                    {"page": page, "box_id": box_id,
                        "question_key": question_key, "ques_idx": ques_idx}
                )
            elif "Table" in ap_matchedRow["bucketurl"]:
                ap_line = ap_matchedRow["correctLine"]
                section_content.append({
                    "type": "table",
                    "content": ap_line,
                    "ap_type": ap_type,
                    "page": page,
                    "box_id": box_id
                })
                absorbed_section_boxes.append(
                    {"page": page, "box_id": box_id,
                        "question_key": question_key, "ques_idx": ques_idx}
                )
            elif "Title" in ap_matchedRow["bucketurl"]:
                ap_line = ap_matchedRow["correctLine"]
                section_content.append({
                    "type": "title",
                    "content": ap_line,
                    "ap_type": ap_type,
                    "page": page,
                    "box_id": box_id
                })
                absorbed_section_boxes.append(
                    {"page": page, "box_id": box_id,
                        "question_key": question_key, "ques_idx": ques_idx}
                )
            else:
                logger.info(ap_matchedRow)
                logger.info(f"look at this {ap_matchedRow['bucketurl']}")
                raise Exception(f"look at this {ap_matchedRow['bucketurl']}")
                # assert(False)

    return section_title, section_content, absorbed_section_boxes


def do_section_identification_down(new_section_match_map, bbox_map_int, page_box_count):
    full_question_key_absorted = []
    section_content_map = {}
    absorbed_map = {}
    for i, idx in enumerate(new_section_match_map):

        logger.info(
            "==================================== section identification down ===================================== ")

        section_map = []
        absorbed_section_boxes = []  # when we go down, which boxes we added more
        bbox_list = bbox_map_int[idx]
        skip_absorbed_key = []
        section_match_idx = new_section_match_map[idx]
        for section in section_match_idx:
            page = section["page"]
            box_id = section["box_id"]
            question_key = section["question_key"]
            ques_idx = section["ques_idx"]

            section_title = ""
            section_content = []

            logger.info(
                f">>> checking section page: {page}   box_id : {box_id} question key: {question_key} <<<")

            if question_key in skip_absorbed_key:
                logger.info(
                    f"skipping {question_key} because it is already absorbed")
                continue

            matched_box = bbox_list[page][box_id]
            logger.info(matched_box)
            matchedRow = None
            if "matchedRow" in matched_box:
                matchedRow = matched_box["matchedRow"]

            if matchedRow:
                logger.info("found a matched row!")
                ret_section_title, ret_section_content, ret_absorbed_section_boxes = util_match_row(
                    matched_box, page, box_id, question_key, ques_idx)
                if len(ret_section_title) > 0:
                    section_title = ret_section_title
                if len(ret_section_content) > 0:
                    section_content.extend(ret_section_content)
                if len(ret_absorbed_section_boxes) > 0:
                    absorbed_section_boxes.extend(ret_absorbed_section_boxes)

            else:
                # logger.info("this is not a title. need to find surrounding first going down only and finding down limit of section")
                section_content.append({
                    "type": "text",
                    "content": matched_box["line"],
                    "page": page,
                    "box_id": box_id
                })
                absorbed_section_boxes.append(
                    {"page": page, "box_id": box_id,
                        "question_key": question_key, "ques_idx": ques_idx}
                )

            while True:
                box_id += 1
                if page in page_box_count[idx]:
                    max_box_id = page_box_count[idx][page]
                    if box_id >= max_box_id:
                        page += 1
                        box_id = 0
                        if page not in page_box_count[idx]:
                            logger.info(
                                f"breaking page {page} box id {box_id}")
                            break

                else:
                    logger.info(f"breaking page {page} box id {box_id}")
                    break

                logger.info(f"page {page} box id {box_id}")
                sub_matched_box = bbox_list[page][box_id]

                should_break = False

                # check if the next box is either a title or if its matched by another section
                for subsection in section_match_idx:
                    sub_page = subsection["page"]
                    sub_box_id = subsection["box_id"]
                    sub_question_key = subsection["question_key"]
                    if page == sub_page:
                        if box_id == sub_box_id:
                            logger.info(
                                f"sub section exists with a match question key :{question_key}: and sub_question_key :{sub_question_key} sub_page: {sub_page} box id {sub_box_id}")
                            if "_" in question_key:
                                key1 = question_key.split("_")[0]
                                key2 = sub_question_key.split("_")[0]
                                if key1 == key2:
                                    logger.info(
                                        f"is just continuation of keys so will append itself {sub_question_key}")
                                    full_question_key_absorted.append(
                                        sub_question_key)
                                    # absorbed_section_boxes.append(
                                    #     {"page": sub_page, "box_id" : sub_box_id, "question_key": sub_question_key, "ques_idx": ques_idx}
                                    # )
                                    skip_absorbed_key.append(sub_question_key)
                                else:
                                    should_break = True
                                    break
                            else:
                                should_break = True
                                break

                # logger.info(sub_matched_box)
                if not should_break:
                    # if should break means another match was found

                    if "matched" not in sub_matched_box:
                        sub_matched_box["matched"] = False
                        
                    if sub_matched_box["matched"]:
                        bucketurl = sub_matched_box["matchedRow"]["bucketurl"]
                        if "Title" in bucketurl:
                            logger.info("next title found so breaking")
                            should_break = True
                            # we will break it here, so that once traversing up in the next iternatino we can match title.
                            # but then there should be 3rd iteration which doest break on this
                        else:
                            logger.info(
                                f"sub matched addend to content and absorbing it")

                            section_content.append({
                                "type": "line",
                                "content": sub_matched_box["line"],
                                "page": page,
                                "box_id": box_id
                            })
                            absorbed_section_boxes.append(
                                {"page": page, "box_id": box_id,
                                    "question_key": question_key, "ques_idx": ques_idx}
                            )

                    else:

                        line = sub_matched_box["line"]
                        if len(line.strip()) == 0:
                            continue

                        logger.info(f"addend to content and absorbing it")

                        section_content.append({
                            "type": "text",
                            "content": line,
                            "page": page,
                            "box_id": box_id
                        })
                        absorbed_section_boxes.append(
                            {"page": page, "box_id": box_id,
                                "question_key": question_key, "ques_idx": ques_idx}
                        )

                if should_break:
                    logger.info("breaking out")
                    break

            section_map.append({
                "section_title": section_title,
                "question_key": question_key,
                "section_content": section_content
            })

        section_content_map[idx] = section_map
        absorbed_map[idx] = absorbed_section_boxes

    return section_content_map, absorbed_map, full_question_key_absorted


def validate(new_section_match_map, section_content_map, full_question_key_absorted):
    for idx in new_section_match_map:
        new_section_match = new_section_match_map[idx]
        section_contents = section_content_map[idx]
        for section in new_section_match:
            question_key = section["question_key"]
            found = False
            if question_key in full_question_key_absorted:
                found = True
                break

            for content in section_contents:
                if question_key == content["question_key"]:
                    found = True
                    break

            if not found:
                logger.info(f"question key {question_key}")
                raise Exception(f"803: question key {question_key}")
                assert(False)  # debug this


def do_up_section_identification(new_section_match_map, bbox_map_int, page_box_count, absorbed_map):

    up_section_content_map = {}
    up_absorbed_map = {}

    for i, idx in enumerate(new_section_match_map):

        logger.info(
            "==================================== section identification up ===================================== ")

        bbox_list = bbox_map_int[idx]
        section_map = []
        absorbed_section_boxes = []  # when we go up, which boxes we added more

        prev_absorbed_section_boxes = absorbed_map[idx]
        section_match_idx = new_section_match_map[idx]

        for section in section_match_idx:
            page = section["page"]
            box_id = section["box_id"]
            question_key = section["question_key"]
            ques_idx = section["ques_idx"]

            logger.info(
                f">>>> checking section page: {page}   box_id : {box_id} question key: {question_key} page {page} box {box_id} <<<<<")
            matched_box = bbox_list[page][box_id]
            matchedRow = None
            if "matchedRow" in matched_box:
                matchedRow = matched_box["matchedRow"]

            section_title = ""
            section_content = []
            should_parse = False

            if matchedRow:
                if "Title" in matchedRow["bucketurl"]:
                    logger.info("skip as its a matched title")
                    pass
                else:
                    should_parse = True

            else:
                should_parse = True
                logger.info(
                    "this is not a matched row. need to find surrounding first going up only and finding up limit of section")

            if should_parse:
                while True:
                    box_id -= 1
                    if box_id == -1:
                        page -= 1
                        box_id = 0

                    logger.info(f"page {page} box id {box_id}")
                    if page == 0:
                        logger.info(f"breaking page {page} box id {box_id}")
                        break

                    sub_matched_box = bbox_list[page][box_id]
                    should_break = False

                    # check if the next box is either a title or if its matched by another section

                    logger.info(prev_absorbed_section_boxes)
                    for boxes in prev_absorbed_section_boxes:
                        prev_page = boxes['page']
                        prev_box_id = boxes['box_id']
                        # logger.info(f"prev page {prev_page}  prev box id {prev_box_id} page {page} box id {box_id}")
                        if page == prev_page and box_id == prev_box_id:
                            logger.info(
                                f"sub already absorbed section exists with a match question key :{boxes['question_key']}:")
                            should_break = True

                    for subsection in section_match_idx:
                        sub_page = subsection["page"]
                        sub_box_id = subsection["box_id"]
                        sub_question_key = subsection["question_key"]
                        if page == sub_page:
                            if box_id == sub_box_id:
                                logger.info(
                                    f"sub section exists with a match question key :{question_key}: and sub_question_key :{sub_question_key}")
                                if "_" in question_key:
                                    key1 = question_key.split("_")[0]
                                    key2 = sub_question_key.split("_")[0]
                                    if key1 == key2:
                                        logger.info(
                                            f"is just continuation of keys so will append itself")
                                        # absorbed_section_boxes.append(
                                        #     {"page": sub_page, "box_id" : sub_box_id, "question_key": question_key, "ques_idx": ques_idx}
                                        # )
                                        should_break = True
                                    else:
                                        should_break = True
                                        break
                                else:
                                    should_break = True
                                    break

                    if not should_break:
                        # logger.info(sub_matched_box)
                        if "matched" not in sub_matched_box:
                            sub_matched_box["matched"] = False

                        if sub_matched_box["matched"]:

                            if "Title" in sub_matched_box["matchedRow"]["bucketurl"]:
                                should_break = True
                                logger.info(
                                    "breaking as found title, but adding the title as well")

                            ret_section_title, ret_section_content, ret_absorbed_section_boxes = util_match_row(
                                sub_matched_box, page, box_id, question_key, ques_idx)
                            if len(ret_section_title) > 0:
                                section_title = ret_section_title
                            if len(ret_section_content) > 0:
                                section_content.extend(ret_section_content)
                            if len(ret_absorbed_section_boxes) > 0:
                                logger.info("absorted the content")
                                absorbed_section_boxes.extend(
                                    ret_absorbed_section_boxes)
                                # even current match should not get repeated again
                                prev_absorbed_section_boxes.extend(
                                    ret_absorbed_section_boxes)

                        else:

                            line = sub_matched_box["line"]
                            if len(line.strip()) == 0:
                                logger.info("empty line")
                                continue

                            logger.info(
                                f"addend to content and absorbing it page :{page} box id : {box_id}")

                            section_content.append({
                                "type": "text",
                                "content": line,
                                "page": page,
                                "box_id": box_id
                            })
                            absorbed_section_boxes.append(
                                {"page": page, "box_id": box_id,
                                    "question_key": question_key, "ques_idx": ques_idx}
                            )
                            prev_absorbed_section_boxes.append(
                                {"page": page, "box_id": box_id,
                                    "question_key": question_key, "ques_idx": ques_idx}
                            )  # even current match should not get repeated again

                    if should_break:
                        logger.info("breaking")
                        break

            if len(section_content) > 0 or len(section_title) > 0:
                section_map.append({
                    "section_title": section_title,
                    "question_key": question_key,
                    "section_content": section_content
                })

        up_section_content_map[idx] = section_map
        up_absorbed_map[idx] = absorbed_section_boxes

    return up_section_content_map, up_absorbed_map


def create_combined_section_content_map(section_content_map, up_section_content_map):

    combined_section_content_map = {}

    for idx in up_section_content_map:
        up_section_index = up_section_content_map[idx]

        section_index = section_content_map[idx]
        combined_section_content_map[idx] = []
        for section in section_index:
            question_key = section["question_key"]
            for up_section in up_section_index:
                up_question_key = up_section["question_key"]
                if question_key == up_question_key:

                    up_section_title = up_section["section_title"]
                    up_section_content = up_section["section_content"]
                    section_title = section["section_title"]
                    section_content = section["section_content"]

                    if len(up_section_title) > 0 and len(section_title) > 0 and section_title.strip() != up_section_title.strip():
                        logger.info(
                            f"up section title {up_section_title} section_title {section_title}")
                        logger.info(up_section)
                        logger.info(section)
                        raise Exception("995")
                        # assert(False)

                    section = {
                        "question_key": question_key,
                        "section_title": "",
                        "section_content": []
                    }

                    if len(up_section_title) > 0:
                        section["section_title"] = up_section_title

                    section["section_content"] = up_section_content + \
                        section_content

                    break

            combined_section_content_map[idx].append(section)

    return combined_section_content_map


# finally doing another traverse and adding sub titles inside now


def do_subsection_identification(combined_section_content_map, absorbed_map, up_absorbed_map, answer_map, bbox_map_int, page_box_count):

    complete_section_match_map = {}
    complete_absorbed_map = {}

    for i, idx in enumerate(combined_section_content_map):

        logger.info(
            "==================================== section finding sub title sub sections ===================================== ")

        section_map = []
        absorbed_section_boxes = []
        bbox_list = bbox_map_int[idx]
        answer_list = answer_map[idx]
        section_match_idx = combined_section_content_map[idx]
        prev_absorbed_section_boxes = absorbed_map[idx] + up_absorbed_map[idx]

        for ques_idx, section in enumerate(section_match_idx):
            logger.info(section)
            question_key = section["question_key"]
            current_answer = None

            for answer in answer_list:
                if answer == question_key:
                    current_answer = answer_list[question_key]
                    break

            logger.info(
                f">>> checking section page: question key: {question_key} <<<")
            logger.info(section)

            page = 0
            box_id = 0
            for c in section["section_content"]:
                if page < c['page']:
                    page = c['page']

            for c in section["section_content"]:
                if page == c['page']:
                    if box_id < c['box_id']:
                        box_id = c['box_id']

            section_content = section["section_content"]
            section_title = section["section_title"]

            while True:
                box_id += 1
                if page in page_box_count[idx]:
                    max_box_id = page_box_count[idx][page]
                    if box_id >= max_box_id:
                        page += 1
                        box_id = 0
                        if page not in page_box_count[idx]:
                            logger.info(
                                f"breaking page {page} box id {box_id}")
                            break

                else:
                    logger.info(f"breaking 2 page {page} box id {box_id}")
                    break

                logger.info(f"page {page} box id {box_id}")
                sub_matched_box = bbox_list[page][box_id]

                should_break = False

                # logger.info(prev_absorbed_section_boxes)
                # process.ex

                for boxes in prev_absorbed_section_boxes:
                    prev_page = boxes['page']
                    prev_box_id = boxes['box_id']
                    if page == prev_page and box_id == prev_box_id:
                        logger.info(
                            f"sub already absorbed section exists with a match question key :{boxes['question_key']}: and sub_question_key :{boxes['question_key']}")
                        should_break = True

                # logger.info(sub_matched_box)
                if not should_break:
                    # if should break means another match was found

                    if "matched" not in sub_matched_box:
                        sub_matched_box["matched"] = False

                    if sub_matched_box["matched"]:
                        ret_section_title, ret_section_content, ret_absorbed_section_boxes = util_match_row(
                            sub_matched_box, page, box_id, question_key, ques_idx)
                        if len(ret_section_title) > 0:
                            section_content.append({
                                "type": "title",
                                "content": ret_section_title,
                                "page": page,
                                "box_id": box_id
                            })
                        if len(ret_section_content) > 0:
                            section_content.extend(ret_section_content)

                        if len(ret_absorbed_section_boxes) > 0:
                            absorbed_section_boxes.extend(
                                ret_absorbed_section_boxes)

                    else:

                        line = sub_matched_box["line"]
                        if len(line.strip()) == 0:
                            continue

                        logger.info(f"addend to content and absorbing it")

                        section_content.append({
                            "type": "text",
                            "content": line,
                            "page": page,
                            "box_id": box_id
                        })
                        absorbed_section_boxes.append(
                            {"page": page, "box_id": box_id,
                                "question_key": question_key, "ques_idx": ques_idx}
                        )

                if should_break:
                    logger.info("breaking out")
                    break

            if len(section_title) > 0 or len(section_content) > 0:
                section_map.append({
                    "section_title": section_title,
                    "current_answer":  current_answer,
                    "question_key": question_key,
                    "section_content": section_content

                })

        complete_section_match_map[idx] = section_map
        complete_absorbed_map[idx] = absorbed_section_boxes

    return complete_section_match_map, complete_absorbed_map


def get_orphan_section_map(answer_map, bbox_map_int, absorbed_map, up_absorbed_map, complete_absorbed_map):
    orphan_section_map = {}

    for i, idx in enumerate(answer_map):
        bbox_list = bbox_map_int[idx]
        absorted = []
        section_match = []
        up_absorted = []
        up_section_match = []
        if idx in absorbed_map:
            absorted = absorbed_map[idx]
        if idx in up_absorbed_map:
            up_absorted = up_absorbed_map[idx]
        if idx in complete_absorbed_map:
            complete_absorbed = complete_absorbed_map[idx]

        final_absorbed = absorted + up_absorted + complete_absorbed
        orphan_sections = []

        orphan_lines = []

        for page in bbox_list:
            for box_id, bbox in enumerate(bbox_list[page]):
                if len(bbox["line"].strip()) > 0:
                    found = False
                    for row in final_absorbed:
                        if page == row["page"] and box_id == row["box_id"]:
                            found = True

                    if not found:
                        logger.info(
                            f"line not matched.. page {page} box {box_id} {bbox['line']} ")
                            
                        if "matched" not in bbox:
                            bbox["matched"] = False

                        if bbox["matched"]:
                            ret_section_title, ret_section_content, ret_absorbed_section_boxes = util_match_row(
                                bbox, page, box_id, "", -1)
                            if len(ret_section_title) > 0:
                                logger.info(
                                    f"found a title box adding it further page: {page} box_id: {box_id}")
                                orphan_sections.append({
                                    "type": "title",
                                    "content": ret_section_title,
                                    "page": page,
                                    "box_id": box_id
                                })
                            if len(ret_section_content) > 0:
                                logger.info(
                                    f"found a text box adding it further page: {page} box_id: {box_id}")
                                orphan_sections.extend(ret_section_content)
                            else:
                                pass
                        else:
                            line = bbox["line"]
                            if len(line.strip()) == 0:
                                continue

                            print(f"addend to content and absorbing it")

                            orphan_sections.append({
                                "type" : "text",
                                "content": line,
                                "page" : page,
                                "box_id" : box_id
                            })
                            
        if len(orphan_sections) > 0:
            orphan_section_map[idx] = orphan_sections

    return orphan_section_map


def combine_ner_into_entites(tag_dict):
    new_tag_dict = {
        'entities': []
    }
    custom_entities = []

    prev_pos = -99
    custom_start_pos = -99
    entity_str = ""
    prev_label = ''
    prev_label_confidance = 0
    for entity in tag_dict["entities"]:
        new_labels = []

        if 'labels' in entity:
            labels = entity["labels"]

            for label in labels:
                tag = label.to_dict()["value"]
                confidence = label.to_dict()["confidence"]

                entity["type"] = tag
                entity["confidence"] = confidence
                break

            for label in labels:
                new_labels.append(label.to_dict())

            # logger.info(entity)
            start_pos = entity["start_pos"]
            end_pos = entity["end_pos"]
            if tag == prev_label:
                # logger.info(f"end pos {start_pos} and prev pos {prev_pos}")
                if start_pos == prev_pos + 1:
                    # logger.info("continue: ", entity["text"])
                    entity_str += " " + entity["text"]
                    prev_pos = end_pos
                    prev_label = tag
                    prev_label_confidance = confidence
                else:
                    custom_start_pos = start_pos
                    # logger.info("finishing next: ", entity["text"])
                    custom_entities.append({
                        "text": entity_str,
                        "label": prev_label,
                        "start_pos": custom_start_pos,
                        "end_pos": end_pos
                    })
                    # new entity now
                    prev_pos = end_pos
                    prev_label = tag
                    prev_label_confidance = confidence
                    entity_str = entity["text"]
            else:
                if len(entity_str) == 0:
                    # logger.info("frsit time: ", entity["text"])
                    custom_start_pos = start_pos
                    entity_str = entity["text"]
                    prev_pos = end_pos
                    prev_label = tag
                    prev_label_confidance = confidence
                else:
                    # logger.info("finishing next: ", entity["text"])
                    custom_entities.append({
                        "text": entity_str,
                        "label": prev_label,
                        "start_pos": custom_start_pos,
                        "end_pos": end_pos
                    })
                    # new entity now
                    prev_pos = end_pos
                    prev_label = tag
                    prev_label_confidance = confidence
                    entity_str = entity["text"]

        entity['labels'] = new_labels
        new_tag_dict["entities"].append(entity)

    if len(entity_str) != 0:
        custom_entities.append({
            "text": entity_str,
            "label": prev_label,
            "start_pos": custom_start_pos,
            "end_pos": end_pos
        })

    return custom_entities, new_tag_dict


def fix_single_char_line(line):
    single_char_word = 0
    multi_char_word = 0
    # to fix something like this
    # H i g h - T e c h   I n s t i t u t e   ( A n t h e m   C o l l e g e )   C o m p u t e r   N e t w o r k i n g   S a n   D i e g o   U r b a n   L e a g u e   E l e c t r o n i c s   T e c h n i c i a n   C a s t l e   P a r k   H i g h   S c h o o l   A c a d e m i c ,   T e c h n i c a l ,   V o c a t i o n a l
    for word in line.split():
        if len(word.strip()) == 1:
            single_char_word += 1
        else:
            multi_char_word += 1

    if multi_char_word == 0 and len(line.strip().split()) >= 1:
        words = line.split("  ")
        line = " ".join(["".join(word.split(" ")) for word in words])
        logger.info(f"new line space fix {line}")

    return line


questions_heading_map = {
    "personal_name": "CONTACT",
    "summary": "SUMMARY",
    "exp_years": "WORK EXPERIANCE",
    "exp_company": "WORK EXPERIANCE",
    "exp_designation": "WORK EXPERIANCE",
    "exp_duration": "WORK EXPERIANCE",
    # "exp_res": "what are your recent job responsibilities",
    "projects_name": "PROJECTS",
    # "projects_skills": "what skillset or technologies you have used in your most recent projects?",
    "skills": "SKILLS",
    "education_degree": "EDUCATION",
    "education_year": "EDUCATION",
    "certifications": "CERTIFICATIONS",
    "training": "TRAINING",
    "personal_location": "PERSONAL INFO",
    "personal_dob": "PERSONAL INFOMATION",
    "awards": "AWARDS",
    "extra": "EXTRA",
    "references": "REFERENCES"
}
questions_to_direct_answer = ["personal_name", "exp_years", "exp_company",
                              "exp_designation", "exp_duration", "personal_dob", "personal_location"]


sub_question_to_ask = {
    "exp_": {
        "skill": "what skills did you use?",
        "responsiblity": "what are your recent job responsibilities?",
        "project": "what is name of your project?"
    },
    "projects_": {
        "skill": "what skills did you use?",
        "project": "what is name of your project?"
    }
}


def get_tags_subsections_subanswers(complete_section_match_map, tagger):
    section_ui_map = {}
    for idx in complete_section_match_map:
        logger.info(f"idx: {idx}")
        complete_section_match = complete_section_match_map[idx]
        section_ui = {}
        for section in complete_section_match:
            question_key = section['current_answer']['question_key']
            section_ui[question_key] = []

            if question_key in questions_to_direct_answer:
                logger.info(f"qa answer {section['current_answer']['answer']}")

            heading = questions_heading_map[question_key]
            section_ui[question_key].append({
                "type": "heading",
                "text": heading
            })

            sentence = []
            sub_sections = []
            # need to break based on title here as well, but in some cases like in case of personal name etc. we should not do this
            # this is more specific to bigger sections
            if len(section["section_title"]) > 0:
                sentence.append(section["section_title"])
                section_ui[question_key].append({
                    "type": "heading_alternate",
                    "text": fix_single_char_line(section["section_title"])
                })

            display_text = []
            for x in section["section_content"]:
                if x["type"] == "title":
                    if len(sentence) > 0:
                        sub_sections.append(sentence)
                        section_ui[question_key].append({
                            "type": x["type"],
                            "text": fix_single_char_line(" ".join(sentence))
                        })
                        sentence = []

                if isinstance(x["content"], list):
                    for con in x["content"]:
                        new_x_content = []
                        for ll in x["content"]:
                            new_x_content.append(fix_single_char_line(ll))

                        x['content'] = new_x_content
                        sentence.extend(x['content'])
                else:
                    sentence.append(x['content'])

                display_text.append({
                    "type": x["type"],
                    "text": x["content"]
                })

            if len(sentence) > 0:
                sub_sections.append(sentence)
                section_ui[question_key].append({
                    'type': 'text',
                    'sentence': sentence,
                    "display_text": display_text
                })
                sentence = []

            logger.info(f">>>> {section['current_answer']['question_key']}")
            # instead of sub_sections
            for idx2, ui in enumerate(section_ui[question_key]):
                # if ui['type'] == "title" or  ui['type'] == "heading" or  ui['type'] == "heading_alternate":
                #   continue

                if "text" in ui:
                    line = ui['text']
                else:
                    line = " ".join(ui['sentence'])

                logger.info("=================")
                # logger.info(json.dumps(sentence, indent=1))

                logger.info(line)
                logger.info("_____")

                if len(line.strip()) == 0:
                    continue

                logger.info("length line %s", len(line.split(" ")))
                section_ui[question_key][idx2]["questions"] = []
                if len(line.split(" ")) > 10:  # atleast 10 words to ask any questions else no use
                    for key in sub_question_to_ask:
                        if key in section['current_answer']["question_key"] or key == section['current_answer']["question_key"]:
                            for sub_ques_key in sub_question_to_ask[key]:
                                sub_question = sub_question_to_ask[key][sub_ques_key]

                                logger.info("****** asking question *********")
                                logger.info(sub_question)

                                start_time = time.time()
                                try:
                                    if len(line) > 2048:
                                        new_line = line[:2048]
                                    else:
                                        new_line = line

                                    answer = question_answerer({
                                        'question': sub_question,
                                        'context': new_line
                                    }, handle_impossible_answer=True)
                                    logger.info(answer)
                                    section_ui[question_key][idx2]["questions"].append(
                                        answer)
                                    logger.info("time taken for answer :",
                                          time.time() - start_time)
                                    logger.info("context length: ", len(line))

                                except Exception as e:
                                    pass

                logger.info("************extracting tags************")
                start_time = time.time()
                logger.info(f"ner line: {line}")
                if len(line) < 512:
                    sentence = Sentence(line, use_tokenizer=False)
                    tagger.predict(sentence)
                else:
                    sentence = Sentence(line[:512], use_tokenizer=False)
                    tagger.predict(sentence)

                urls = re.findall(
                    "https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+", line)
                if urls:

                    logger.info("found urls:")
                    # in this spaces are coming 5f70cfe80f22e9003956efe4
                    # logger.info(line)
                    logger.info(urls)
                    section_ui[question_key][idx2]["urls"] = urls

                tag_dict = sentence.to_dict(tag_type='ner')
                # for entity in sentence.get_spans('ner'):
                # logger.info(entity)
                # logger.info(json.dumps(tag_dict, indent=1, default=str))
                # logger.info(tag_dict)
                custom_entities, new_tag_dict = combine_ner_into_entites(
                    tag_dict)
                section_ui[question_key][idx2]["tags"] = custom_entities
                logger.info(json.dumps(custom_entities, indent=1))
                logger.info("time taken for answer : %s", time.time() - start_time)
                logger.info("----------------------------------")

        section_ui_map[idx] = section_ui

    return section_ui_map


