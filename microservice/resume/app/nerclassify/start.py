from app.logging import logger
import logging
import json
# from app import mongo
from app.cvlinepredict.start import predict as predictLineLabel


def start(isTesting=False):
    if isTesting:
        logger.setLevel(logging.INFO)
    else:
        logger.setLevel(logging.CRITICAL)
        data = getFilesToParseFromDB()
        process(data)


def process(data, isPageWiseData=False):

    extractEntity = {}
    finalEntity = {}

    finalEntity["wrkExp"] = []
    finalEntity["education"] = []

    combinData = {}
    for rowIdx in range(len(data)):
        row = data[rowIdx]
        combinData[rowIdx] = []

        file = row["file"]
        logger.info("cv name %s", file)
        nerparsed = row["nerparsed"]

        if isPageWiseData:
            row["compressedStructuredContent"] = {}
            for cvpage in range(1, 10):
                # max 10 cv page
                cvpage = str(cvpage)
                if cvpage in row and "compressedStructuredContent" in row[cvpage]:
                    row["compressedStructuredContent"][cvpage] = json.loads(
                        row[cvpage]["compressedStructuredContent"])
                else:
                    break

        for pageno, pagedata in enumerate(nerparsed):
            pageno += 1  # start from page 1 and not 0
            # page level
            if pageno not in extractEntity:
                extractEntity[pageno] = {}

            startIdx = 0
            nerline = []
            for lineno, line in enumerate(pagedata):
                logger.debug(line)

                lineData = line["lineData"]
                contentIdx = line["contentIdx"]

                if lineno not in extractEntity[pageno]:
                    extractEntity[pageno][lineno] = {}

                text = line["line"]
                prevPos = 0
                if len(line["entity"]["entities"]) > 0:
                    for ent in line["entity"]["entities"]:
                        start_pos = ent["start_pos"]
                        end_pos = ent["end_pos"]
                        enttype = ent["type"]
                        text = ent["text"]

                        if enttype in extractEntity[pageno][lineno]:
                            if start_pos - prevPos <= 3:
                                # assume same word
                                extractEntity[pageno][lineno][enttype][-1] += " " + text
                                prevPos = end_pos
                            else:
                                # new enitty
                                prevPos = end_pos
                                extractEntity[pageno][lineno][enttype].append(
                                    text)

                        else:
                            prevPos = end_pos
                            if enttype not in extractEntity[pageno][lineno]:
                                extractEntity[pageno][lineno][enttype] = []
                                extractEntity[pageno][lineno][enttype].append(
                                    text)

                    logger.debug(extractEntity[pageno][lineno])
                    logger.debug(line["line"])
                    logger.debug(line["entity"]["entities"])

                    # CARDINAL, Designation, EducationDegree, ORG,  DATE
                    # Skills,
                    # ExperianceYears
                    # DOB, Email, GPE, PERSON, Phone, Language

                    singleEntity = ["PERSON", "Phone",
                                    "Email", "DOB", "GPE", "LANGUAGE"]
                    finalEntity, foundEntity = updateSingleEntity(
                        singleEntity, extractEntity[pageno][lineno], finalEntity, pageno, contentIdx)

                    if "PERSON" in extractEntity[pageno][lineno] and ("Phone" in extractEntity[pageno][lineno] or "Email" in extractEntity[pageno][lineno]):
                        extractEntity[pageno][lineno]["classify"] = "CONTACT"
                        for cIDx in contentIdx:
                            row["compressedStructuredContent"][str(
                                pageno)][cIDx]["classify"] = "CONTACT"
                            row["compressedStructuredContent"][str(
                                pageno)][cIDx]["classifyreason"] = "person and (Phone or Email)"
                            row["compressedStructuredContent"][str(
                                pageno)][cIDx]["contentIdx"] = contentIdx


                    if "Phone" in extractEntity[pageno][lineno] and "Email" in extractEntity[pageno][lineno]:
                        extractEntity[pageno][lineno]["classify"] = "CONTACT"
                        for cIDx in contentIdx:
                            row["compressedStructuredContent"][str(
                                pageno)][cIDx]["classify"] = "CONTACT"
                            row["compressedStructuredContent"][str(
                                pageno)][cIDx]["classifyreason"] = "(Phone or Email)"
                            row["compressedStructuredContent"][str(
                                pageno)][cIDx]["contentIdx"] = contentIdx

                    if "DOB" in extractEntity[pageno][lineno] or "LANGUAGE" in extractEntity[pageno][lineno]:
                        extractEntity[pageno][lineno]["classify"] = "ENDINFO"
                        for cIDx in contentIdx:
                            row["compressedStructuredContent"][str(
                                pageno)][cIDx]["classify"] = "ENDINFO"
                            row["compressedStructuredContent"][str(
                                pageno)][cIDx]["classifyreason"] = "dob and language"
                            row["compressedStructuredContent"][str(
                                pageno)][cIDx]["contentIdx"] = contentIdx

                    if "ORG" in extractEntity[pageno][lineno]:
                        if "Designation" in extractEntity[pageno][lineno] and "EducationDegree" in extractEntity[pageno][lineno]:
                            logger.info(
                                "this has both designation and degree")
                            logger.info(
                                "need to review this as well why this happened? both designation and exp degree")
                            logger.info(extractEntity[pageno][lineno])
                            logger.info(line["line"])
                            # we can look at heading also in such cases. if it matches
                            # we ca also if it matched a table it should education mostly
                            # this is happening in cases of accounts which i have seen. where Cost Accountant looks like a degree as well and a education qualification also
                            extractEntity[pageno][lineno]["classify"] = "ERROR"
                            lineLabel = predictLineLabel(line["line"])
                            extractEntity[pageno][lineno]["classifyNN"] = lineLabel
                            for cIDx in contentIdx:
                                
                                row["compressedStructuredContent"][str(
                                    pageno)][cIDx]["classify"] = "ERROR"
                                row["compressedStructuredContent"][str(
                                    pageno)][cIDx]["classifyNN"] = lineLabel
                                row["compressedStructuredContent"][str(
                                    pageno)][cIDx]["classifyreason"] = "org and designation and degree"
                                row["compressedStructuredContent"][str(
                                    pageno)][cIDx]["contentIdx"] = contentIdx

                        if "Designation" in extractEntity[pageno][lineno]:
                            logger.info("this line looks like work exp")

                            obj = []

                            for org in extractEntity[pageno][lineno]["ORG"]:
                                obj.append({
                                    "org": org,
                                    "pageno" : pageno,
                                    "contentIdx" : contentIdx
                                })

                            relatedKeys = ["Designation",
                                           "DATE", "ExperianceYears"]

                            for key in relatedKeys:
                                if key in extractEntity[pageno][lineno]:
                                    for idx, value in enumerate(extractEntity[pageno][lineno][key]):
                                        if idx > len(obj) - 1:
                                            obj.append({
                                                "org": "",
                                                "pageno" : pageno,
                                                "contentIdx" : contentIdx
                                            })
                                        obj[idx][key] = value

                            finalEntity["wrkExp"].append(obj)
                            extractEntity[pageno][lineno]["classify"] = "WRKEXP"

                            for cIDx in contentIdx:
                                row["compressedStructuredContent"][str(
                                    pageno)][cIDx]["classify"] = "WRKEXP"
                                row["compressedStructuredContent"][str(
                                    pageno)][cIDx]["classifyreason"] = "org and designation"
                                row["compressedStructuredContent"][str(
                                    pageno)][cIDx]["contentIdx"] = contentIdx

                        elif "EducationDegree" in extractEntity[pageno][lineno]:
                            logger.info("this line looks like education")

                            obj = []

                            for org in extractEntity[pageno][lineno]["ORG"]:
                                obj.append({
                                    "org": org,
                                    "pageno" : pageno,
                                    "contentIdx" : contentIdx
                                })

                            relatedKeys = [
                                "EducationDegree", "DATE", "CARDINAL"]
                            for key in relatedKeys:
                                if key in extractEntity[pageno][lineno]:
                                    for idx, value in enumerate(extractEntity[pageno][lineno][key]):
                                        if idx > len(obj) - 1:
                                            obj.append({
                                                "org": "",
                                                "pageno" : pageno,
                                                "contentIdx" : contentIdx

                                            })
                                        obj[idx][key] = value

                            finalEntity["education"].append(obj)
                            extractEntity[pageno][lineno]["classify"] = "EDU"
                            for cIDx in contentIdx:
                                row["compressedStructuredContent"][str(
                                    pageno)][cIDx]["classify"] = "EDU"
                                row["compressedStructuredContent"][str(
                                    pageno)][cIDx]["classifyreason"] = "org and education"
                                row["compressedStructuredContent"][str(
                                    pageno)][cIDx]["contentIdx"] = contentIdx

                        elif "ExperianceYears" in extractEntity[pageno][lineno]:
                            logger.info(
                                "this is work exp has there is exp years")
                            obj = []

                            for org in extractEntity[pageno][lineno]["ORG"]:
                                obj.append({
                                    "org": org,
                                    "pageno" : pageno,
                                    "contentIdx" : contentIdx
                                })

                            relatedKeys = [
                                "DATE", "Designation", "ExperianceYears"]

                            for key in relatedKeys:
                                if key in extractEntity[pageno][lineno]:
                                    for idx, value in enumerate(extractEntity[pageno][lineno][key]):
                                        if idx > len(obj) - 1:
                                            obj.append({
                                                "org": "",
                                                "pageno" : pageno,
                                                "contentIdx" : contentIdx

                                            })

                                        obj[idx][key] = value

                            finalEntity["wrkExp"].append(obj)
                            extractEntity[pageno][lineno]["classify"] = "WRKEXP"
                            for cIDx in contentIdx:
                                row["compressedStructuredContent"][str(
                                    pageno)][cIDx]["classify"] = "WRKEXP"
                                row["compressedStructuredContent"][str(
                                    pageno)][cIDx]["classifyreason"] = "org and exp yrs"
                                row["compressedStructuredContent"][str(
                                    pageno)][cIDx]["contentIdx"] = contentIdx

                        else:
                            logger.info(
                                "need to review this as well why this happened")
                            logger.info(
                                "unable to find.... maybe check with Pvt University etc texts")
                            org = (
                                " ".join(extractEntity[pageno][lineno]["ORG"][0])).lower()
                            if "pvt" in org or "ltd" in org or "limi" in org:
                                logger.info("looks like a company")
                                extractEntity[pageno][lineno]["classify"] = "WRK"
                                for cIDx in contentIdx:
                                    row["compressedStructuredContent"][str(
                                        pageno)][cIDx]["classify"] = "WRK"
                                    row["compressedStructuredContent"][str(
                                        pageno)][cIDx]["classifyreason"] = "org and pvt ltd"
                                    row["compressedStructuredContent"][str(
                                        pageno)][cIDx]["contentIdx"] = contentIdx
                            elif "university" in org or "col" in org or "school" in org:
                                logger.info("look like college")
                                extractEntity[pageno][lineno]["classify"] = "WRK"
                                for cIDx in contentIdx:
                                    row["compressedStructuredContent"][str(
                                        pageno)][cIDx]["classify"] = "EDU"
                                    row["compressedStructuredContent"][str(
                                        pageno)][cIDx]["classifyreason"] = "org and college"
                                    row["compressedStructuredContent"][str(
                                        pageno)][cIDx]["contentIdx"] = contentIdx
                            else:
                                logger.info(
                                    "we will look at this in this? company or univ")
                                logger.info(line["line"])
                                # we can look at heading also in such cases. if it matches
                                # we ca also if it matched a table it should education mostly
                                # . mostly it will be company only. if we find another line with edu means this a company == this is wrong because many due to education being a table it goes on multiple lines
                                extractEntity[pageno][lineno]["classify"] = "ERROR"
                                lineLabel = predictLineLabel(line["line"])
                                extractEntity[pageno][lineno]["classifyNN"] = lineLabel
                                for cIDx in contentIdx:
                                    row["compressedStructuredContent"][str(
                                        pageno)][cIDx]["classify"] = "ERROR"
                                    row["compressedStructuredContent"][str(
                                        pageno)][cIDx]["classifyNN"] = lineLabel
                                    row["compressedStructuredContent"][str(
                                        pageno)][cIDx]["classifyreason"] = "org and not college or not pvt ltd"
                                    row["compressedStructuredContent"][str(
                                        pageno)][cIDx]["contentIdx"] = contentIdx

                    elif "Designation" in extractEntity[pageno][lineno] and "ExperianceYears" in extractEntity[pageno][lineno]:
                        logger.info(
                            "this looks like summary and current designation and exp")
                        extractEntity[pageno][lineno]["classify"] = "SUMMARY"
                        for cIDx in contentIdx:
                            row["compressedStructuredContent"][str(
                                pageno)][cIDx]["classify"] = "SUMMARY"
                            row["compressedStructuredContent"][str(
                                pageno)][cIDx]["classifyreason"] = "summary and current designation"
                            row["compressedStructuredContent"][str(
                                pageno)][cIDx]["contentIdx"] = contentIdx
                            logger.info(extractEntity[pageno][lineno])
                            finalEntity, foundEntity = updateSingleEntity(
                                ["Designation", "ExperianceYears"], extractEntity[pageno][lineno], finalEntity, pageno, contentIdx)
                    elif "ExperianceYears" in extractEntity[pageno][lineno]:
                        logger.info(
                            "need to review this why this happened? orpahn ExperianceYears")
                        logger.info(extractEntity[pageno][lineno])
                        if lineno > 0 and extractEntity[pageno][lineno - 1] == "WRK":
                            if "ExperianceYears" in finalEntity["wrkExp"][-1]:
                                finalEntity["wrkExp"].append({
                                    "obj": "",
                                    "ExperianceYears": " ".join(extractEntity[pageno][lineno]["ExperianceYears"]),
                                    "pageno" : pageno,
                                    "contentIdx" : contentIdx
                                })
                                extractEntity[pageno][lineno]["classify"] = "WRK"
                                for cIDx in contentIdx:
                                    row["compressedStructuredContent"][str(
                                        pageno)][cIDx]["classify"] = "WRK"
                                    row["compressedStructuredContent"][str(
                                        pageno)][cIDx]["classifyreason"] = "exp yr and prev work"
                                    row["compressedStructuredContent"][str(
                                        pageno)][cIDx]["contentIdx"] = contentIdx

                            else:
                                finalEntity["wrkExp"][-1]["ExperianceYears"] = " ".join(
                                    extractEntity[pageno][lineno]["ExperianceYears"])
                        else:
                            # finalEntity, foundEntity = updateSingleEntity(
                            #     ["ExperianceYears"], extractEntity[pageno][lineno], finalEntity, pageno, contentIdx)
                            # i dont think we should update experiance years without work
                            # getting wrong data updated on 17th Nov 2020
                            pass

                    elif "Designation" in extractEntity[pageno][lineno]:
                        logger.info(
                            "need to review this why this happened? orpahn Designation")
                        logger.info(extractEntity[pageno][lineno])
                        if lineno > 0 and extractEntity[pageno][lineno - 1] == "WRK":
                            if "Designation" in finalEntity["wrkExp"][-1]:
                                finalEntity["wrkExp"].append({
                                    "obj": "",
                                    "Designation": " ".join(extractEntity[pageno][lineno]["Designation"]),
                                    "pageno" : pageno,
                                    "contentIdx" : contentIdx
                                })
                                extractEntity[pageno][lineno]["classify"] = "WRK"
                                for cIDx in contentIdx:
                                    row["compressedStructuredContent"][str(
                                        pageno)][cIDx]["classify"] = "WRK"
                                    row["compressedStructuredContent"][str(
                                        pageno)][cIDx]["classifyreason"] = "designation and prev work"
                                    row["compressedStructuredContent"][str(
                                        pageno)][cIDx]["contentIdx"] = contentIdx
                            else:
                                finalEntity["wrkExp"][-1]["Designation"] = " ".join(
                                    extractEntity[pageno][lineno]["Designation"])
                        else:
                            finalEntity, foundEntity = updateSingleEntity(
                                ["Designation"], extractEntity[pageno][lineno], finalEntity, pageno, contentIdx)
                    elif "EducationDegree" in extractEntity[pageno][lineno]:
                        # if previous line is education, we can append it to that
                        logger.info(
                            "need to review this why this happened? orphan EducationDegree")
                        logger.info(extractEntity[pageno][lineno])
                        if lineno > 0 and extractEntity[pageno][lineno - 1] == "EDU":
                            if "EducationDegree" in finalEntity["education"][-1]:
                                finalEntity["education"].append({
                                    "obj": "",
                                    "EducationDegree": " ".join(extractEntity[pageno][lineno]["EducationDegree"]),
                                    "pageno" : pageno,
                                    "contentIdx" : contentIdx
                                })
                                extractEntity[pageno][lineno]["classify"] = "EDU"
                                for cIDx in contentIdx:
                                    row["compressedStructuredContent"][str(
                                        pageno)][cIDx]["classify"] = "EDU"
                                    row["compressedStructuredContent"][str(
                                        pageno)][cIDx]["classifyreason"] = "degree and prev edu"
                                    row["compressedStructuredContent"][str(
                                        pageno)][cIDx]["contentIdx"] = contentIdx
                            else:
                                finalEntity["education"][-1]["EducationDegree"] = " ".join(
                                    extractEntity[pageno][lineno]["EducationDegree"])
                        else:
                            finalEntity, foundEntity = updateSingleEntity(
                                ["EducationDegree"], extractEntity[pageno][lineno], finalEntity, pageno, contentIdx)
                    elif "DATE" in extractEntity[pageno][lineno]:
                        logger.info(
                            "need to review this why this happened? orphan Date")
                        # if previous line is education, we can append it to that
                        logger.info(extractEntity[pageno][lineno])
                        if lineno > 0 and extractEntity[pageno][lineno - 1] == "EDU":
                            if "DATE" in finalEntity["wrkExp"][-1]:
                                finalEntity["wrkExp"].append({
                                    "obj": "",
                                    "DATE": " ".join(extractEntity[pageno][lineno]["Date"]),
                                    "pageno" : pageno,
                                    "contentIdx" : contentIdx
                                })
                                extractEntity[pageno][lineno]["classify"] = "EDU"
                                for cIDx in contentIdx:
                                    row["compressedStructuredContent"][str(
                                        pageno)][cIDx]["classify"] = "EDU"
                                    row["compressedStructuredContent"][str(
                                        pageno)][cIDx]["classifyreason"] = "date and prev edu"
                                    row["compressedStructuredContent"][str(
                                        pageno)][cIDx]["contentIdx"] = contentIdx

                            else:
                                finalEntity["wrkExp"][-1]["DATE"] = " ".join(
                                    extractEntity[pageno][lineno]["DATE"])
                        else:
                            finalEntity, foundEntity = updateSingleEntity(
                                ["Date"], extractEntity[pageno][lineno], finalEntity, pageno, contentIdx)
                    else:
                        if not foundEntity:
                            logger.info(
                                "need to review this why this happened?")
                            logger.info(extractEntity[pageno][lineno])
                            logger.info("unknow ....")
                        pass
                else:
                    if len(text.strip()) > 0: 
                        for cIDx in contentIdx:
                            lineLabel = predictLineLabel(line["line"])
                            row["compressedStructuredContent"][str(
                                pageno)][cIDx]["classifyNN"] = lineLabel
                            row["compressedStructuredContent"][str(
                                pageno)][cIDx]["classify"] = "NOENTITY"
                            row["compressedStructuredContent"][str(
                                            pageno)][cIDx]["contentIdx"] = contentIdx
                    
        logger.info("classification all lines of cv now")

        for key in row["compressedStructuredContent"].keys():
            for didx, drow in enumerate(row["compressedStructuredContent"][key]):
                if "classify" in drow:
                    logger.info(drow["line"])
                    logger.info(drow["classify"])
                else:
                    if "matchedRow" in drow:
                        logger.debug(drow["line"])
                        logger.debug("unclassify")

            # break # need only page 1
        logger.info(json.dumps(finalEntity, indent=1, sort_keys=False))
        logger.info(json.dumps(extractEntity,
                               indent=1, sort_keys=False))

        # if "wrkExp" in finalEntity:
        #     del finalEntity["wrkExp"]
        # if "Designation" in finalEntity:
        #     del finalEntity["Designation"]
        # if "ExperianceYears" in finalEntity:
        #     del finalEntity["ExperianceYears"]
        # uncomment this once finalized qa with ui
        

        combinData[rowIdx] = {
            "finalEntity": finalEntity,
            "extractEntity": extractEntity,
            "compressedStructuredContent": row["compressedStructuredContent"]
        }
        # if "_id" in row:
        #     mongo.db.cvparsingsample.update_one({"_id": row["_id"]},
        #                                         {
        #         "$set": {
        #             "nerExtracted": True,
        #             "finalEntity": json.dumps(finalEntity),
        #             "extractEntity": json.dumps(extractEntity),
        #             "compressedStructuredContent": row["compressedStructuredContent"]
        #         }
        #     }
        #     )

        logger.info("total lines %s", len(nerparsed))

    return combinData


def getFilesToParseForTesting():
    return []


def getFilesToParseFromDB():

    ret = mongo.db.cvparsingsample.find({"nerparsed": {"$exists": True}, "nerExtracted": {
        "$exists": False}, "nerparsedv3": True})
    # .limit(1).skip( random.randint(0,250) )

    data = []
    for row in ret:
        data.append(row)

    return data


def updateSingleEntity(singleEntity, entityLine, finalEntity,pageno,contentIdx):
    foundEntity = False
    for entityName in singleEntity:
        if entityName in entityLine:
            foundEntity = True
            if entityName not in finalEntity:
                finalEntity[entityName] = ""

            entities = entityLine[entityName]
            for ent in entities:
                if len(finalEntity[entityName]) == 0:
                    finalEntity[entityName] = {
                        "obj" : ent,
                        "pageno" : pageno,
                        "contentIdx" : contentIdx
                    }
                else:
                    if "additional-" + entityName not in finalEntity:
                        finalEntity["additional-" + entityName] = []

                    finalEntity["additional-" + entityName].append(ent)

    return finalEntity, foundEntity
