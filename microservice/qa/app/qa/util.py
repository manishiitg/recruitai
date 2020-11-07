def clean_page_content_map(idx, page_contents):

    page_content_map = {}

    content = "\n".join(page_contents).replace("\n\n\n","").replace(u'\xa0', u' ')

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
            # print("some issue with line %s", line)
            line = "".join(line.split(" "))
            # print("new line %s", line)

        cleanLineData.append(line)
            
    line_without_space = 0
    for line in cleanLineData:
        if " " not in line.strip() and len(line) > 10: # if more than 10 its not a single word
            line_without_space += 1
        else:
            words = line.split(" ")
            if len(words) == 2:
                line_without_space += 1

    if (line_without_space > len(cleanLineData) / 2) and len(cleanLineData) > 10:
        print("line issue skipping")
        # print(content)
        return None

    page_content_map[idx] = "\n".join(cleanLineData)

    return page_content_map