from pdfminer.pdfpage import PDFTextExtractionNotAllowed
from pdfminer.high_level import extract_text
import subprocess
from app.logging import logger
import time


def get_content_from_resume(cv, cvpage, timeAnalysis, fileIdx, cvpages):
    start_time = time.time()
    logger.critical("cv page %s", cvpage)
    try:
        if cvpage == -1:
            content = extract_text(cv)
        else:
            content = extract_text(cv, page_numbers=[cvpage-1], maxpages=1)
            

        content = str(content)
        #content = textract.process(cv , page_numbers=[cvpage-1], maxpages=1)
    except PDFTextExtractionNotAllowed as e:
        logger.critical(e)
        # if filestoparse[fileIdx]["id"] != -1:
        #   mongo.db.cvparsingsample.update_one({"_id" : filestoparse[fileIdx]["id"]},
        #     {
        #         "$set" : {
        #           "error" : str(e)
        #         }
        #     }
        #   )
        logger.critical("skipping due to error in cv extration %s ", cv)
        content = get_content_from_text_extract(cv, cvpage)
    except Exception as e:
        logger.critical(
            "general exception in trying nodejs text cv extration %s %s ", str(e), cv)
        content = get_content_from_text_extract(cv, cvpage)

    content = clean_page_content_map(content)
    if content is None:
        logger.critical("getting content from pdf2 json")
        content = get_content_from_pdf2_json(cv, cvpage)
        content = clean_page_content_map(content)
        if content is None:
            logger.critical("getting content text extract")
            content = get_content_from_text_extract(cv, cvpage)
            content = clean_page_content_map(content)

    if content is None:
        try:
            logger.critical("getting content from ocr")
            content = get_content_from_ocr(cv, cvpage)
        except Exception as e:
            logger.critical("XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX %s", str(e))
            return "", timeAnalysis
        
    if fileIdx != -1:
        timeAnalysis[fileIdx]["extract_text" +
                            str(cvpages)] = time.time() - start_time
    
    return content, timeAnalysis

def get_content_from_ocr(cv, cvpage):
    cv_tff = cv.replace(".pdf",".tiff")
    if cvpage == -1:
        x = subprocess.check_output(
            ['convert -density 300 ' + cv + " -depth 8 -strip -background white -alpha off " + cv_tff], shell=True, timeout=60)
    else:
        x = subprocess.check_output(
            ['convert -density 300 ' + cv+"["+ str(cvpage-1) +"]" + " -depth 8 -strip -background white -alpha off " + cv_tff], shell=True, timeout=60)
    
    # print(x)
    cv_output = cv.replace(".pdf","")
    x = subprocess.run(['tesseract', cv_tff, cv_output], stdout=subprocess.PIPE)
    with open(cv_output + ".txt") as f:
        s = f.read()
        return s
    
    return None
        
    # print(x)
import os.path
def get_content_from_pdf2_json(cv, cvpage):
    # ----------------Page (0) Break----------------
    cv_text = cv.replace(".pdf",".content.txt")

    try:
        x = subprocess.check_output(['pdf2json -f ' + cv + " -c -s"], shell=True, timeout=60)
    except subprocess.TimeoutExpired as e:
        return None
    
    x = x.decode("utf-8")
    # print('pdf2json -f ' + cv + " -c -s")
    # print(x)
    if not os.path.isfile(cv_text):
        return None 
        
    with open(cv_text) as f:
        s = f.read()
        if "----------------Page" in s:
            pages = s.split("----------------Page")
        else:
            pages = s.split("Break------------")

        if cvpage == -1:
            return "\n\n".join(pages)
        else:
            return pages[cvpage -1]
    
    return None



def get_content_from_text_extract(cv, cvpage):
    try:
        x = subprocess.check_output(
        ['pdf-text-extract ' + cv], shell=True, timeout=60)
        x = x.decode("utf-8")
    except Exception as e:
        logger.critical("exception %s", e)
        return None
    
    # x = re.sub(' +', ' ', x)
    # logger.critical("=======================")
    # logger.critical(x)
    # logger.critical("=======================")

    x = x.replace("[ '", "")
    x = x.replace("['", "")
    x = x.replace("' ]", "")
    x = x.replace("']", "")
    if "'," in x:
        pages_data_extract = x.split("',")
    else:
        pages_data_extract = [x]

    logger.critical("***************************")
    logger.critical(f"len(pages_data_extract) {len(pages_data_extract)} cvpage {cvpage}")
    
    if cvpage == -1:
        final_content = []
        for content in pages_data_extract:
            if content.count("+") > 5:
                # '                                   SHAZ JAMAL\n' +
                # '               20/1A A.K MD SIDDIQUE LANE TALTALA, Kolkata, West Bengal -\n' +
                # '                                       700016\n' +
                # '                            7980873732, 9431050837   shazjamal94@gmail.com\n' +
                # '\n' +
                # '\n' +
                # '\n' +
                # '\n' +
                # 'SKILL                                         OBJECTIVE\n' +
                # '\n' +
                # 'Frameworks                                    Self-motivated and hardworking graduat
                lines = content.split("+")
                newline = []
                for line in lines:
                    line = line.replace("'","")
                    newline.append(line)
                content = " ".join(newline)
                final_content.append(content)
            else:
                final_content.append(content) 

        content = "\n\n".join(final_content)
    else:
        # print(pages_data_extract)
        # i dont know why this is happning maybe empty page in resume or something
        if (cvpage-1) >= len(pages_data_extract):
            return ""

        content = pages_data_extract[cvpage-1]
        if content.count("+") > 5:
            # '                                   SHAZ JAMAL\n' +
            # '               20/1A A.K MD SIDDIQUE LANE TALTALA, Kolkata, West Bengal -\n' +
            # '                                       700016\n' +
            # '                            7980873732, 9431050837   shazjamal94@gmail.com\n' +
            # '\n' +
            # '\n' +
            # '\n' +
            # '\n' +
            # 'SKILL                                         OBJECTIVE\n' +
            # '\n' +
            # 'Frameworks                                    Self-motivated and hardworking graduat
            lines = content.split("+")
            newline = []
            for line in lines:
                line = line.replace("'","")
                newline.append(line)
            content = " ".join(newline)

    logger.critical(content)

    
    logger.critical("***************************")
    return content


def clean_page_content_map(page_contents):
    if not page_contents:
        return None 

    page_content_map = {}

    if isinstance(page_contents, list):
        content = "\n".join(page_contents).replace(
            "\n\n\n", "").replace(u'\xa0', u' ')
    else:
        content = page_contents.replace("\n\n\n", "").replace(u'\xa0', u' ')

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
        if len(line.strip()) == 0:
            continue
        #  HighSchoolfrom RPICKALYANPURJAUNPUR2013withaggregate
        #  HighSchoolfrom RPICKALYANPURJAUNPUR2013withaggregate
        #  Intermediatefrom RPICKALYANPURJAUNPUR2015withaggregate78%
        #  Ihavedone1yearpreprationofIITJEE(2015-2016).
        # 5fb505b9bea0290084140944
        # one cv has many lines like this
        max_word_len = 20  # assuming most words are under twenlty letters
        # if more than 10 its not a single word
        if len(line.strip().split(" ")) <= 2 and len(line) > 30:
            if "@" in line or "://" in line:
                continue
            # print("issue line: ", line)
            line_without_space += 1
        else:
            words = line.split(" ")
            big_word_count = 0
            small_word_count = 0
            for word in words:
                if len(word) > max_word_len:
                    big_word_count += 1
                elif len(word) > 2:  # alteast should have two characters
                    small_word_count += 1

            if big_word_count >= small_word_count and big_word_count != 0:
                if "@" in line or "://" in line:
                    continue
                # print("issue line: ", line)
                line_without_space += 1

    if ((line_without_space > len(cleanLineData) * .1) and len(cleanLineData) > 10) or (len(cleanLineData) == 1):
        # if line_without_space > 15:
        # print(f"line_without_space {line_without_space}")
        # print(f"len(cleanLineData) {len(cleanLineData)}")
        # print(content)
        return None

    return "\n".join(cleanLineData)
