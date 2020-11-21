from app.logging import logger
import collections
from fuzzywuzzy import fuzz
import re
import math
import copy


def finalCompressedContent(cleanLineData, jsonOutput, seperateTableLineMatchedIndexes, logger, predictions):
    matchIdx = []

    structuredContent = []

    lineNonMatchList = {}

    for row in jsonOutput:
        if "isClaimed" not in row:
            row["isClaimed"] = False

    lineIdx = 0

    claimedLinesIDX = []  # use when lines are claimed but in between excluded as well

    lineData = cleanLineData

    while lineIdx < len(lineData):
        logger.info("=====: %s", lineIdx)

        if lineIdx in claimedLinesIDX:
            lineIdx += 1
            continue

        line = lineData[lineIdx]
        logger.info("=====: %s", line)
        # some times getting headings like this K A M N A M A D H W A N I , S K I L L S this is causing issue.
        # so need to check for this and fix
        maxwordLength = 0
        for w in line.split(" "):
            if len(w) > maxwordLength:
                maxwordLength = len(w)

        if maxwordLength == 1:
            line = "".join(line.split(" "))

        isTableIdx = False
        tableIdxRow = False
        for tableIndex, tableMatchRows in enumerate(seperateTableLineMatchedIndexes):
            tableIndexes = tableMatchRows["lineIds"]
            if lineIdx in tableIndexes:
                isTableIdx = True
                tableIdxRow = tableMatchRows["row"]
                break

        if isTableIdx:
            logger.debug("%s ::this is already matched with a table ", line)
            structuredContent.append({
                "line": line,
                "lineIdx": lineIdx,
                "isTable": True,
                "matchedRow": tableIdxRow,
                "tableIndex": tableIndex,
                "matched": True,
                "finalClaimedIdx": tableIdxRow["orgIdx"]
            })
            lineIdx += 1
            continue

        isLineMatchFound = True

        words = line.split(" ")
        if len(words) <= 2:
            logger.info("is orphan? %s", line)

            maxratio = 0
            maxRow = False
            for rowidx, row in enumerate(jsonOutput):
                if "isClaimed" in row and row["isClaimed"]:
                    continue
                correctLine = row["correctLine"]
                ratio = fuzz.ratio(line, correctLine)
                logger.debug("%s orphan ratio %s line %s correctLine",
                             ratio, line, correctLine)
                if ratio > 90 and ratio > maxratio:
                    maxRow = row
                    row["idx"] = rowidx
                    maxratio = ratio

            if maxRow:
                jsonOutput[maxRow["idx"]]["isClaimed"] = True
                jsonOutput[maxRow["idx"]]["matchRatio"] = {
                    "ratio": ratio,
                    "line": line,
                    "isOrphan": True
                }
                logger.debug('oraphan: %s matched with ratio: %s  with %s',
                             line, maxratio, maxRow["correctLine"])

                structuredContent.append({
                    "line": line,
                    "lineIdx": lineIdx,
                    "orphan": True,
                    "matchedRow": maxRow,
                    "matched": True,
                    "finalClaimedIdx": maxRow["idx"]
                })

            else:

                # need to deal with orphans better.
                # i am assume orphans to be heading. which is correct if we get a bounding box for it
                # but if i am not getting bbo xthat means it can be part of table or something as well.
                # or a text written in column

                # if i don't have bbox i cannot find any near element as well.
                # so let's just combine the text together?
                # update on 27th. improving this algo futher. as mentioned on top of this block
                if len(structuredContent) > 0:
                    prevRow = structuredContent[-1]
                else:
                    prevRow = []

                # logger.debug(prevRow)
                # if ("orphan" in prevRow and "matchedRow" not in prevRow) or
                if "isTable" in prevRow:
                    prevRow["line"] += " " + line
                    logger.debug("append orphan with prev line")
                    if "appened" not in prevRow:
                        prevRow["appened"] = []

                    prevRow["appened"].append(line)
                    structuredContent[-1] = prevRow
                else:
                    structuredContent.append({
                        "line": line,
                        "orphan": True,
                        "matched": False,
                        "lineIdx": lineIdx
                    })

                    localLineNonMatchList = checkOccuranceOfLineInAllBlocks(
                        line, jsonOutput)
                    lineNonMatchList[lineIdx] = localLineNonMatchList
                    # above two lines should be commented. this is just for test

            lineIdx += 1
            continue

        else:

            # identify if a line is a list because things like 1.  or a.  etc not identified by ocr very well right now
            # doing it a bad way without regex
            isStartingWithList = False
            numbers = [" "]
            for nn in range(20):  # assume max list size of 20
                numbers.append(str(nn))

            patterns = [" ", ".", ")", "#", "¢", "►"]

            for n in numbers:
                for p in patterns:
                    if n == p:
                        continue

                    indexOfList = n + p

                    if line.startswith(indexOfList):
                        # this looks like a list
                        logger.debug("looks like a list %s", line)
                        line = line[len(indexOfList):].strip()
                        isStartingWithList = True
                        break

            # let's find is this text is avaiable
            logger.info({"pdf line": line})
            matchStrIndex = 2

            finalMatchedRow = False
            isConflictResolved = False

            backupBestRow = False
            backupBestIdx = False
            # this is for direct match of string.

            finalClaimedIdx = False
            iter_count = 0
            while not isConflictResolved:
                iter_count += 1
                # conflict can arise because matchString can match multiple line in jsonoutput
                # so we need to find the best math
                matchString = " ".join(line.split(" ")[0:matchStrIndex])
                if len(matchString) < 5: # and matchStrIndex == 2 commented this on 14 nov, not sure why. just because its not on google colab code
                    matchStrIndex += 1
                    logger.debug(matchStrIndex)
                    logger.debug(len(line.split(" ")))
                    if matchStrIndex > len(line.split(" ")) and iter_count > 100:  # new code add much later on this was doing in infinite loop thats why this was added.
                        pass
                    else:
                        continue

                matchString = matchString.replace("\n", " ").strip()
                if not isStartingWithList:
                    # this is because some times fist character is not properly matched in ocr
                    matchString = matchString[1:]
                logger.info("match string is %s", matchString)
                # this is to do extact string match.
                # this means that if our matchString is found exactly in jsonOutput
                howManyMatchStringFound, matchLines = countMatchString(
                    matchString, jsonOutput)

                if howManyMatchStringFound > 1:
                    # if it does then increase match string lenght by one and check again for conflict.
                    if matchStrIndex >= 5:
                        logger.info(
                            "didn't match for even 4 index resolving by taking lowest index of match")
                        lowIdx = 9999
                        logger.info(matchLines)
                        jsonIdx = -1
                        for mi, mrow in enumerate(matchLines):
                            idx = mrow["correctLine"].lower().index(
                                matchString.lower())
                            if idx < lowIdx:
                                lowIdx = idx
                                jsonIdx = mrow["idx"]
                                correctLine = mrow["correctLine"]

                        finalMatchedRow = jsonOutput[jsonIdx]
                        jsonOutput[jsonIdx]["isClaimed"] = True
                        finalClaimedIdx = jsonIdx
                        logger.info("clamed this json id %s", finalClaimedIdx)
                        isConflictResolved = True

                    # sometimes what happens is that when we increase a word then no string matches
                    # i.e with 2 words we had 3 string match, but with 3 words we have zero. this is problem
                    # because we loose the string totally.

                    lowIdx = 9999
                    for mi, mrow in enumerate(matchLines):
                        idx = mrow["correctLine"].lower().index(
                            matchString.lower())
                        if idx < lowIdx:
                            lowIdx = idx
                            backupBestIdx = mrow["idx"]
                            backupBestRow = mrow

                    matchStrIndex += 1
                else:
                    if howManyMatchStringFound == 1:
                        correctLine = matchLines[0]["correctLine"]
                        jsonOutput[matchLines[0]["idx"]]["isClaimed"] = True
                        finalClaimedIdx = matchLines[0]["idx"]
                        logger.info("clamed this json id %s", finalClaimedIdx)
                        finalMatchedRow = matchLines[0]

                    isConflictResolved = True

            if howManyMatchStringFound == 0:
                if backupBestRow:
                    logger.info("we have backup so no need for fuzzy")
                    correctLine = backupBestRow["correctLine"]
                    jsonOutput[backupBestIdx]["isClaimed"] = True
                    finalClaimedIdx = backupBestIdx
                    logger.info("clamed this json id %s", finalClaimedIdx)
                    finalMatchedRow = backupBestRow

                else:
                    matchedRow, matchedRowIdx = doFuzzyMatch(line, jsonOutput)
                    if matchedRow:
                        logger.info("found via fuzzy!")
                        correctLine = matchedRow["correctLine"]
                        jsonOutput[matchedRowIdx]["isClaimed"] = True
                        finalClaimedIdx = matchedRowIdx
                        logger.info("clamed this json id %s", finalClaimedIdx)
                        finalMatchedRow = matchedRow
                    else:
                        logger.info(
                            "there is a pblm, no match string matched")
                        localLineNonMatchList = checkOccuranceOfLineInAllBlocks(
                            line, jsonOutput)
                        lineNonMatchList[lineIdx] = localLineNonMatchList
                        # above two lines should be commented. this is just for test

                        structuredContent.append({
                            "line": line,
                            "nomatch": True,
                            "matched": False,
                            "lineIdx": lineIdx
                        })
                        lineIdx += 1
                        continue

            logger.info("found starting matching string in line %s",
                         finalMatchedRow["correctLine"])

            # if jsonIdx in matchIdx:
            # logger.debug("conflict!!! row already matched?? skipping match")
            # we not let this happen. initally itself we should match against all string and see if conflict happens.
            # continue

            # else:
            # now we need to follow the output and form a full sentence
            # lets find last 2 words of the current sentence and match till its found in the original sentence
            correctLine = re.sub('\s+', ' ', correctLine).strip()
            # ok.... some thing strange happend here.
            # for a specific case  Accountants, Hyderabad. was the last 2 word of every sentence in a list.
            # so it was breaking at the second line itself instead of going to the last line of the list.
            # e.g cv 934.pdf
            # hence i need to make the -2 dynamic

            octMatchCountWords = -2
            ocrMatchString = " ".join(
                correctLine.split(" ")[octMatchCountWords:])

            while(True):
                if correctLine.count(ocrMatchString) == 1 or octMatchCountWords*-1 >= 8:
                    break
                else:
                    octMatchCountWords -= 1
                    ocrMatchString = " ".join(
                        correctLine.split(" ")[octMatchCountWords:])

            logger.info("ocr match string %s", ocrMatchString)
            # ocrMatchString = ocrMatchString[:-1]
            #  not needed since already using fuzzy match
            # this is because some times last character is not properly matched in ocr
            ocrStringLen = len(correctLine)

            searchLen = 0
            # lets find the end
            newLine = []
            internalLineIdx = lineIdx
            fullFuzzRatio = []
            finalMatchRatio = 0
            excludeLowMatchIdx = []
            prevMaxFullMatchRatio = False
            while(True):
                if internalLineIdx >= len(lineData):
                    logger.info("all lines finished breaking out")
                    break

                newNextLine = False
                logger.info("... %s ", lineData[internalLineIdx])
                if internalLineIdx == lineIdx:
                    nline = lineData[lineIdx]
                    newLineIdx = list(range(lineIdx, lineIdx + 1))
                    newLine = [nline]
                else:
                    if internalLineIdx + 1 >= len(lineData):
                        logger.info("all lines finished breaking out")
                        break
                    newLineIdx = list(range(lineIdx, internalLineIdx + 1))
                    newLineIdx = [
                        x for x in newLineIdx if x not in excludeLowMatchIdx]
                    nline = [lineData[iiiidx] for iiiidx in newLineIdx]
                    newLine = nline
                    nline = " ".join(nline)
                    newNextLine = lineData[internalLineIdx]

                searchLen = len(nline)

                # this is an exception in this logic especially for multi columns
                # if suppose some small text comes in between from some other column
                # this will cause either the ratio to go down slightly or maybe stay the same.
                # problem is our code won't know about it all. because the text is small size and ratio will be above 85
                # and this text will absorb it fully.....
                # this is an issue

                if newNextLine and len(fullFuzzRatio) > 0 and len(newNextLine.split(" ")) > 1:
                    # we will check this only after we have found some sort of coherance in text............
                    # hmmmmm... not sure about above as well. if needed or not.......
                    ratio3 = fuzz.partial_ratio(newNextLine, correctLine)
                    logger.info(
                        "partial ratio3 for just the next line %s", ratio3)
                    if ratio3 < 70:
                        logger.info(
                            "ratio3 is quite low....... this can be a problem.")
                        logger.info(
                            "this would be mean the this next doesn't belong this sequence and has come in between by mistake.")
                        # should i check if there is a high match in some other text???
                        foundhighmatch = False
                        for testrow in jsonOutput:
                            ratio3test = fuzz.partial_ratio(
                                newNextLine, testrow["correctLine"])
                            if ratio3test > 90:
                                logger.info(
                                    "ok, there is a high match on some other line as well ....... %s", testrow["correctLine"])
                                foundhighmatch = True
                                break

                        if foundhighmatch:
                            # how.....
                            logger.info("we should skip this in this batch")
                            excludeLowMatchIdx.append(internalLineIdx)
                            internalLineIdx += 1
                            logger.info("going to next line..")
                            # many time when we go to next line we just break out this will result in exclude Not getting any effect
                            newLineIdx = list(
                                range(lineIdx, internalLineIdx + 1))
                            newLineIdx = [
                                x for x in newLineIdx if x not in excludeLowMatchIdx]
                            nline = [lineData[iiiidx] for iiiidx in newLineIdx]
                            newLine = nline
                            nline = " ".join(nline)
                            continue

                ratio = fuzz.ratio(ocrMatchString, " ".join(
                    nline.split(" ")[-octMatchCountWords:]))
                logger.info(
                    "ocrMatchString.lower() %s  === lines substring %s", ocrMatchString,  nline)
                logger.info("line:# %s", nline)
                logger.debug(" ===== ratio %s ==ocr match string %s   concat line %s",
                             ratio, ocrMatchString,  " ".join(nline.split(" ")[-octMatchCountWords:]))

                ratio2 = fuzz.ratio(correctLine, nline)
                logger.info("ratio of full line match %s", ratio2)
                logger.info("correctLine.lower() %s", correctLine)
                logger.info("line.lower() %s", nline.lower())

                # new exprimental
                if prevMaxFullMatchRatio and ratio2 < prevMaxFullMatchRatio:
                    logger.info(
                        "exprimental....ratio2 got reduce we should breakout and remove the last added line as well")
                    newLineIdx = list(range(lineIdx, internalLineIdx + 1 - 1))
                    newLineIdx = [
                        x for x in newLineIdx if x not in excludeLowMatchIdx]
                    nline = [lineData[iiiidx] for iiiidx in newLineIdx]
                    newLine = nline
                    nline = " ".join(nline)
                    break

                if ratio2 > 85:
                    prevMaxFullMatchRatio = ratio2
                    logger.debug(
                        "this means we have somthing. for a large text is there is 85% match its something for sure")
                    fullFuzzRatio.append({
                        "ratio": ratio2,
                        "internalLineIdx": internalLineIdx + 1
                    })

                if ocrMatchString.lower() in nline.lower() or ratio > 90:  # or ratio2 > 85
                    # lineIdx = internalLineIdx # we are not doing this any more rather skipping with claimedidx array
                    finalMatchRatio = ratio
                    logger.debug("found ocr match string in line %s", nline)

                    break
                else:
                    internalLineIdx += 1
                    logger.debug("going to next line..")

                if searchLen > ocrStringLen * (1.5):
                    if len(fullFuzzRatio) > 0:
                        maxRatio = 0
                        maxRatioIdx = 0
                        for ratioRow in fullFuzzRatio:
                            if ratioRow["ratio"] > maxRatio:
                                maxRatio = ratioRow["ratio"]
                                maxRatioIdx = ratioRow["internalLineIdx"]

                        logger.info("found match via full matching itself")

                        newLineIdx = list(range(lineIdx, maxRatioIdx + 1))
                        logger.debug("before idx %s", newLineIdx)
                        newLineIdx = [
                            x for x in newLineIdx if x not in excludeLowMatchIdx]
                        logger.debug("after excluding idx %s", newLineIdx)
                        # logger.debug(newLineIdx, "xxxxx", lineIdx, maxRatioIdx)
                        # newLine = lineData[lineIdx:maxRatioIdx]
                        nline = [lineData[iiiidx] for iiiidx in newLineIdx]
                        finalMatchRatio = maxRatio
                        # lineIdx = maxRatioIdx  # we are not doing this any more rather skipping with claimedidx array
                        break

                    else:
                        logger.debug(
                            "#########################break out of while loop some problem as search has gone very long########################")
                        newLine = []
                        jsonOutput[finalClaimedIdx]["isClaimed"] = False
                        break

            if len(newLine) > 0:
                combinedLine = " ".join(newLine)
                logger.info("final combined line is %s", combinedLine)
                logger.info("idx is at %s", lineIdx)
                import json
                logger.info("new lineeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee %s", json.dumps(newLine, indent=1))
                sortLines = {}
                for ix, txl in enumerate(newLine):
                    sortLines[newLineIdx[ix]] = txl

                claimedLinesIDX.extend(newLineIdx)

                # sortLInes are used later down steam. basically we need to remember the original indexes of the lines as well
                # which we are joining here to form the line

                jsonOutput[finalClaimedIdx]["matchRatio"] = {
                    "ratio": finalMatchRatio,
                    "line": combinedLine,
                    "isOrphan": False
                }

                structuredContent.append({
                    "line": combinedLine,
                    "matched": True,
                    "matchedRow": finalMatchedRow,
                    "lineIdx": lineIdx,
                    "finalClaimedIdx": finalClaimedIdx,
                    "sortLines": sortLines
                })
            else:
                localLineNonMatchList = checkOccuranceOfLineInAllBlocks(
                    line, jsonOutput)
                lineNonMatchList[lineIdx] = localLineNonMatchList
                # above two lines should be commented. this is just for test
                structuredContent.append({
                    "line": line,
                    "noendfound": True,
                    "matched": False,
                    "lineIdx": lineIdx
                })

        lineIdx += 1

    # checking all no match string for occurance

    logger.debug("checking all occurances again.......")
    logger.debug("<<<<<<<<<<<<<<<<<<<<>>>>>>>>>>>>>>>>>>")
    logger.debug("<<<<<<<<<<<<<<<<<<<<>>>>>>>>>>>>>>>>>>")
    logger.debug("<<<<<<<<<<<<<<<<<<<<>>>>>>>>>>>>>>>>>>")
    logger.debug("<<<<<<<<<<<<<<<<<<<<>>>>>>>>>>>>>>>>>>")

    newNonMatchList = {}
    for stIdx, stRow in enumerate(structuredContent):
        if not stRow["matched"]:
            localLineNonMatchList = checkOccuranceOfLineInAllBlocks(
                stRow["line"], jsonOutput)
            lineIdx = stRow["lineIdx"]
            if len(localLineNonMatchList) == 0 and lineIdx in lineNonMatchList and len(lineNonMatchList[lineIdx]) > 0:
                logger.debug(
                    "<<<<<<<<<<<<<<<<<<review this. there seems to some issue>>>>>>>>>>>>>>>>>>>>>>>>")
            else:
                if len(localLineNonMatchList) > 0:
                    maxRatio = 0
                    for m in localLineNonMatchList:
                        if m["ratio2"] > maxRatio:
                            maxRatio = m["ratio2"]

                    maxRows = []
                    for m in localLineNonMatchList:
                        if m["ratio2"] == maxRatio:
                            maxRows.append(m)

                    newNonMatchList[lineIdx] = {
                        "stIdx": stIdx,
                        "stRow": stRow,
                        "maxRows": maxRows
                    }
                else:
                    logger.debug(
                        "i guess detectron2 just didn't match this text.... but we need to keep it as is in final text")
                    structuredContent[stIdx]["strayText"] = True

    logger.debug("<<<<< final calclulations >>>")
    for matchIdx in newNonMatchList.keys():

        logger.debug("match IDx %s", matchIdx)
        # newNonMatchList[matchIdx]
        # "ratio2" : ratio2,
        # "row" : row,
        # "lineIdx" : lineIdx

        stIdx = newNonMatchList[matchIdx]["stIdx"]
        stRow = newNonMatchList[matchIdx]["stRow"]
        maxRows = newNonMatchList[matchIdx]["maxRows"]
        finalMaxRow = False

        logger.debug("line: %s", stRow["line"])

        if len(maxRows) == 1:
            logger.debug("only one row matched")
            finalMaxRow = maxRows[0]
            logger.debug("%s ratio2 %s line idx %s line ",
                         finalMaxRow["ratio2"], finalMaxRow["lineIdx"], finalMaxRow["row"]["correctLine"])
        else:
            logger.debug("multiple rows matched")

            for m in maxRows:
                logger.debug("ratio2 %s line idx %s line %s",
                             m["ratio2"], m["lineIdx"], m["row"]["correctLine"])

            nextMaxRows = False
            nextIdx = matchIdx + 1
            prevIdx = matchIdx - 1
            if nextIdx in newNonMatchList:
                logger.debug("next row is also matched")
                nextMaxRows = newNonMatchList[nextIdx]["maxRows"]

            elif prevIdx in newNonMatchList:
                logger.debug("prev row matched")
                nextMaxRows = newNonMatchList[prevIdx]["maxRows"]
            else:
                logger.debug("neight prev nor next row matched")

            if nextMaxRows:
                if len(nextMaxRows) > 1:
                    logger.debug("multiple next max row")

                    found = False
                    for m in maxRows:

                        for nm in nextMaxRows:
                            if nm["lineIdx"] == m["lineIdx"]:
                                finalMaxRow = m
                                found = True
                                break

                        if found:
                            break

                else:
                    logger.debug("only single next max row")
                    for m in maxRows:
                        logger.debug(
                            "%s == %s", m["lineIdx"],  nextMaxRows[0]["lineIdx"])
                        if m["lineIdx"] == nextMaxRows[0]["lineIdx"]:
                            finalMaxRow = m
                            break

            else:
                logger.debug(
                    " nooo next id....... what to do ignore???? need to think.. assuming the first for now ")
                # is this a very small i.e orphan then just ignore or......
                # i saw this case happen when both text's were same i.e detectron2 matched same text twice
                # as list and text. hence it was matching in both...
                # for now let's just pick any.........
                finalMaxRow = maxRows[0]

        if finalMaxRow:
            logger.debug("found a final row %s", finalMaxRow["lineIdx"])

            # finalMaxRow["lineIdx"] # this is the lineIdx with which we have matched stuff i.e
            # non matched line is found is another claimed row and this is the index of it in jsonOutput Array

            # no i need to find which structuredContent got assigned this?

            # jsonDataIdx = stRow["lineIdx"]
            foundMatchingStruct = False
            for sttIdx, row in enumerate(structuredContent):
                if row["matched"] and row["finalClaimedIdx"] == finalMaxRow["lineIdx"]:
                    logger.debug(
                        "found the structured content where we have insert this line some how")
                    logger.debug(row)
                    # ok. this is a major issue now how to insert content in this.
                    # right now logic is the content will be inserted based on lineIDX i.e original line order.
                    # for this to happen i need to change full line content and sort it
                    # we can also do this in terms of string match indexes. to get more accurate.....
                    if "sortLines" not in row:
                        row["sortLines"] = {
                            row["finalClaimedIdx"]: row["line"]

                        }
                    

                    logger.info("@#$#@$#################################@$#@$#@$#@$#@$#@$#@$#@$#@$#@4")
                    row["sortLines"][stRow["lineIdx"]] = stRow["line"]
                    foundMatchingStruct = True

                    structuredContent[sttIdx] = row
                    break

            if not foundMatchingStruct:
                logger.debug("didn't find matching structure...........")
                if finalMaxRow["ratio2"] > 95:
                    logger.debug(
                        "there is a high match. in this we can see if there are any unclaimed rows")
                    if not jsonOutput[finalMaxRow["lineIdx"]]["isClaimed"]:
                        logger.debug("found the unclamed line, lets claim it?")
                        jsonOutput[finalMaxRow["lineIdx"]]["isClaimed"] = True
                        jsonOutput[finalMaxRow["lineIdx"]]["matchRatio"] = {
                            "ratio": finalMaxRow["ratio2"],
                            "line": stRow["line"],
                            "isOrphan": False
                        }

                        structuredContent[stIdx] = {
                            "line": stRow["line"],
                            "matched": True,
                            "matchedRow": jsonOutput[finalMaxRow["lineIdx"]],
                            # "lineIdx": lineIdx,
                            "finalClaimedIdx": finalMaxRow["lineIdx"],
                            # "sortLines" : sortLines,
                            "prevStruct": stRow
                        }

        else:
            logger.debug("unable to find a final row")


    for sttIdx, row in enumerate(structuredContent):
      if row["matched"] and "sortLines" in row:
        sortLines = row["sortLines"]
        od = collections.OrderedDict(sorted(sortLines.items()))
        logger.debug(od)
        finalLine = " ".join([item[1]  for item in od.items()])
        logger.debug("final reconstruced line %s", finalLine)
        structuredContent[sttIdx]['line'] = finalLine

    ###############################################################
    
    finalStructureContent = compressTables(structuredContent)
    
    logger.debug("+++++++++++++++++++++++++++++Only Matched Content+++++++++++++++++++++++++++++++++++++++++++")
    for rr in finalStructureContent:
      if not rr["matched"]:
        continue 
      logger.debug(rr["line"])

    logger.debug("++++++++++++++++++++++++++++++Stay Text and Matched Content++++++++++++++++++++++++++++++++++++++++++")
    for rr in finalStructureContent:
      if not rr["matched"] and "strayText" not in rr:
        continue 
      logger.debug(rr["line"])


    

    ###############################################################

    newstructuredContent = generateContentWithBBox(finalStructureContent, predictions)

    ###############################################################

    compressedStructuredContent = compressContent(finalStructureContent)

    for row in compressedStructuredContent:
      logger.debug(row["line"])

    # print(json.dumps(jsonOutput, indent=1))
    logger.debug("++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")

    return compressedStructuredContent, newstructuredContent


def chooseBBoxVsSegment(jsonOutput, jsonOutputbbox):
    tableRow = []
    finalJsonOutput = []
    if len(jsonOutput) == 0:
        jsonOutput = jsonOutputbbox

    for i, row in enumerate(jsonOutput):
        # we will remove the bbox images from this and keep only one.
        # either the bbox image or the roi image
        filename = row['filename']
        filename = filename.replace("_ocr", "").replace("_withdpi", "")
        confidance = row["confidance"]
        if "_Table_" in filename:
            row["orgIdx"] = i
            tableRow.append(row)

        avgconf = 0
        for c in confidance:
            avgconf += c

        avgconf = avgconf/len(confidance)
        foundBbox = False
        useOrig = False
        for j, row2 in enumerate(jsonOutputbbox):
            filename2 = row2["filename"].replace("_bbox_", "").replace(
                "_ocr", "").replace("_withdpi", "")
            # logger.debug(filename , " ==== " , filename2)
            if filename == filename2:
                foundBbox = True
                useOrig = True
                confidance2 = row2["confidance"]
                avgconf2 = 0
                for c2 in confidance2:
                    avgconf2 += c2

                avgconf2 = avgconf2/len(confidance2)

                if avgconf2 < avgconf:
                    logger.debug(
                        "not using bbox since conf is low %s < %s", avgconf2, avgconf)
                    useOrig = False
                else:
                    logger.debug("using bbo only %s > %s", avgconf2, avgconf)

                break

        if not foundBbox:
            logger.debug("bbox not found")
            logger.debug(filename)

        if not useOrig:
            finalJsonOutput.append(row)
        else:
            finalJsonOutput.append(row2)
    return finalJsonOutput, tableRow


def identifyTableData(lineData, tableRow, jsonOutput):

    tableLineMatchedIndexes = []
    seperateTableLineMatchedIndexes = []

    for tableIdx, row in enumerate(jsonOutput):
        row["isClaimed"] = False

    for tableIdx, row in enumerate(tableRow):
        row["isMatched"] = False

    if len(tableRow) > 0:
        fuzzRatioToleranceLevels = [95, 80]
        errorCountToleranceLevels = [2, 5]
        # if we have table we have to match it for sure.
        # because form what i am seeing percentage are not getting parse prperly like 69% etc are like not parsed at all by ocr
        # in few cases
        # and table are mostly used for academic qualification only. so this is a problem.
        # hence we need to reduce tolenace if table are not matched.
        # if we have table from detectron means we need to find text for it
        # i am also seeing full words not getting parsed by ocr in a table.....
        # solved the above issue by using opencv and removing broder from table..
        for levelIdx in range(len(fuzzRatioToleranceLevels)):
            fuzzRatioTolerance = fuzzRatioToleranceLevels[levelIdx]
            errorCountTolerance = errorCountToleranceLevels[levelIdx]
            for tableIdx, row in enumerate(tableRow):
                if row["isMatched"]:
                    continue

                text = row["text"]
                # text = row["correctLine"]  # does not work with this
                text = text.replace("\n", " ")
                logger.info("table text: %s", text)
                lineIdx = 0
                while lineIdx < len(lineData):
                    if lineIdx in tableLineMatchedIndexes:
                        logger.info("already matched to a table")
                        lineIdx += 1
                        continue
                    line = lineData[lineIdx]
                    ratio = fuzz.partial_ratio(line, text)

                    totalMatches = 0
                    if ratio > fuzzRatioTolerance or line in text:
                        logger.info("line : %s", line)
                        logger.info("ratio %s", ratio)
                        tableMatches = [line]
                        logger.info('we might have something?')
                        totalMatches += 1
                        # need we need to see how may consicutive matches do we have
                        # should be ateast 5
                        checkLineIdx = lineIdx
                        errorCount = 0
                        tableMatches = []
                        localtableLineMatchedIndexes = [checkLineIdx]
                        while (True and checkLineIdx < len(lineData) - 1):
                            checkLineIdx += 1
                            line = lineData[checkLineIdx]
                            logger.info("line : %s", line)
                            ratio = fuzz.partial_ratio(line, text)
                            logger.info("ratio : %s", ratio)

                            if ratio < fuzzRatioTolerance:
                                if line in text:
                                    logger.info("full match")
                                    totalMatches += 1
                                    localtableLineMatchedIndexes.append(
                                        checkLineIdx)
                                    continue

                                errorCount += 1
                                # its possible as i have seen in cases in between 1 or 2 lines come which are invalid....
                                # hence we cannot totally break out at as
                                # but we will break out after maximum 2 errors
                                if errorCount > errorCountTolerance:
                                    logger.info("it broke out")
                                    break
                            else:
                                totalMatches += 1
                                localtableLineMatchedIndexes.append(
                                    checkLineIdx)
                                tableMatches.append(line)

                        if totalMatches >= 5:
                            tableLineMatchedIndexes.extend(
                                localtableLineMatchedIndexes)
                            seperateTableLineMatchedIndexes.append({
                                "lineIds": localtableLineMatchedIndexes,
                                "row": row
                            })
                            logger.info(
                                "ok we found a table match ########################### level %s", levelIdx + 1)
                            tableRow[tableIdx]["isMatched"] = True
                            logger.info(
                                jsonOutput[tableRow[tableIdx]["orgIdx"]]["correctLine"])
                            jsonOutput[tableRow[tableIdx]
                                       ["orgIdx"]]["isClaimed"] = True
                            jsonOutput[tableRow[tableIdx]["orgIdx"]]["matchRatio"] = {
                                "ratio": fuzzRatioTolerance,
                                "line": "",
                                "isOrphan": False,
                                "isTable": True
                            }
                            break
                        else:
                            logger.info(
                                "we couldn't find a table??????????????????????????")

                    lineIdx += 1

                if tableRow[tableIdx]["isMatched"] is False:
                    logger.info(
                        "unable to find any match for this table %%%%%%%%%%%%%%%%%%%%%%%%%%")

    else:
        logger.info("no tables found via detectron! life is simple :P")

    logger.info("actual no of tables %s", len(tableRow))
    logger.info("table matches done %s", len(seperateTableLineMatchedIndexes))
    return seperateTableLineMatchedIndexes, jsonOutput

# a) table are matched first and all words are assigned to it
# ... i think it should remove table from further matching
# b) we try to find starting of text using extract match and fuzzy match
# if there is a match, then we try to match the end of the text
# to find the end i match either the end of the string
# or i try to match full string and see if there is atlast an 85% match of full string
# c) for orphans, i try to match it with headings only if not i just combine two orphans together.

# wwhat i need to change, since i have much better detectron matching now than before
# a) is fine, remove it from further down string matching
# b) see if i am able to match full lists or not. because if its a large text block, sometimes
# some random text comes it been and this breaks the full string matching.
# especially if column layout is 2 column. sometime time left column text comes in between
# the right column and due to which full text matching doesn't happen
# c) oraphas are not just headings, these can part of a text as well. like group of skills
# or a group of text like contact info in left column. or any small box if its in left column can form orphans
# so i need to do partial match as well and if multiple consicutive matches occur maybe its part of it?

# basically in short, i need to try to match more of text with ocr as i have very good detection in ocr now in most cases...
# so need to match text as much as possible. instead of not matching it....


def doFuzzyMatch(inputLine, jsonOutput):
    logger.debug(" %s 0000000000000000", inputLine)
    words = inputLine.split(" ")
    matchedRow = False
    matchedRowIdx = False
    if len(words) >= 5:
        # this is a bigger line we can match more words
        logger.debug("doing bigger fuzzy matching")
        maxratio = 0
        matchString = " ".join(words[0:5])
        # this is used because in a very large text, the first word was not properly convert to ocr
        # due to this entire text was not combined
        for rowidx, row in enumerate(jsonOutput):
            if "isClaimed" in row and row["isClaimed"]:
                continue
            correctLine = row["correctLine"]
            if len(correctLine.split(" ")) > 5:

                ratio = fuzz.ratio(matchString, " ".join(
                    correctLine.split(" ")[0:5]))
                logger.debug('%s match string %s ocr string %s', ratio,
                             matchString.lower(), " ".join(correctLine.split(" ")[0:5]))
                if ratio > 80 and ratio > maxratio:
                    maxratio = ratio
                    matchedRow = row
                    matchedRowIdx = rowidx

    if len(words) >= 3 and matchedRowIdx is False:
        logger.debug("final match fuzzy")
        maxratio = 0
        matchString = " ".join(words[0:3])
        # this is used because in a very large text, the first word was not properly convert to ocr
        # due to this entire text was not combined
        for rowidx, row in enumerate(jsonOutput):
            if "isClaimed" in row and row["isClaimed"]:
                continue
            correctLine = row["correctLine"]
            if len(correctLine.split(" ")) > 3:

                ratio = fuzz.ratio(matchString, " ".join(
                    correctLine.split(" ")[0:3]))
                logger.debug(' %s match string %s  ocr string %s', ratio,
                             matchString, " ".join(correctLine.split(" ")[0:3]))
                if ratio > 80 and ratio > maxratio:
                    maxratio = ratio
                    matchedRow = row
                    matchedRowIdx = rowidx

    return matchedRow, matchedRowIdx


def countMatchString(matchString, jsonOutput):
    howManyMatchStringFound = 0
    matchLines = []
    for idx, row in enumerate(jsonOutput):
        if "isClaimed" in row and row["isClaimed"]:
            continue
        correctLine = row["correctLine"]
        logger.debug("%s match substring: %s  correct line %s", matchString.lower(
        ) in correctLine.lower(), matchString.lower(), correctLine.lower())
        if matchString.lower() in correctLine.lower():
            row["idx"] = idx
            matchLines.append(row)
            howManyMatchStringFound += 1

    return howManyMatchStringFound, matchLines


def checkOccuranceOfLineInAllBlocks(line, jsonOutput):
    logger.debug("checking occurance of line in all blocks... %s", line)
    localLineNonMatchList = []
    for rowidx, row in enumerate(jsonOutput):
        # we need to check across all rows now.
        # we should't match all lines. we should check with matchRatio score of other line of other lines

        if "isClaimed" in row and row["isClaimed"]:

            # if "matchRatio" not in row:
            # logger.debug(rowidx, " <<< this condition should never happen")

            if row["matchRatio"]["isOrphan"]:
                continue

            if row["matchRatio"]["ratio"] > 95:
                continue

        correctLine = row["correctLine"]
        # this is a problem. 
        # this line • AMCAT Certificate (Software Development Trainee) is getting matched with "at" because of partial ratio

        len_diff = abs(len(line) - len(correctLine))

        len_diff_percentage = (len_diff / len(line))
        if len_diff_percentage < .1:
            ratio2 = fuzz.ratio(line, correctLine)
        else:
            ratio2 = fuzz.partial_ratio(line, correctLine)

        logger.debug("ratio2 %s  matched with %s", ratio2, correctLine)
        if ratio2 > 90:
            # this is possible match in another block
            localLineNonMatchList.append({
                "ratio2": ratio2,
                "row": row,
                "lineIdx": rowidx
            })
            logger.debug("matched!!!!!!!!!!!")

    return localLineNonMatchList


def compressTables(newstructuredContent):
    finalStructureContent = []
    # this is just compressing all table rows into single row
    for idx, row in enumerate(newstructuredContent):
        if not row["matched"] and "strayText" not in row:
            if "strayText" in row:
                finalStructureContent.append(row)
            continue
        if "isTable" in row and row["isTable"]:
            tableIndex = row["tableIndex"]
            foundTable = False
            tableFoundIdx = False
            for idx2, row2 in enumerate(finalStructureContent):
                if "isTable" in row2 and row2["isTable"] and row2["tableIndex"] == tableIndex:
                    foundTable = True
                    tableFoundIdx = idx2
                    break

            if foundTable:
                finalStructureContent[tableFoundIdx]["line"] = finalStructureContent[tableFoundIdx]["line"] + " " + row["line"]
            else:
                finalStructureContent.append(row)

        else:
            finalStructureContent.append(row)

    return finalStructureContent


def generateContentWithBBox(structuredContent , predictions):
    newstructuredContent = []
    for rr in structuredContent:
        if not rr["matched"] and "strayText" not in rr:
            if "strayText" in rr:
                structuredContent.append(rr)
            continue
        if "matchedRow" in rr:
            rr["matchedRow"].pop('confidance', None)

            filename = rr["matchedRow"]["filename"]
            for ppage in predictions:
                for p in ppage["instances"]:
                    filename = filename.replace("_ocr", "")
                    filename = filename.replace("_withdpi", "")
                    if p["filename"] == filename or p["finalfilenamebbox"] == filename:
                        rr["matchedRow"]["bbox"] = p["bbox"].tolist()
                        rr["matchedRow"]["imagesize"] = (
                            ppage["imagewidth"], ppage["imageheight"])
                        break

        rr["isboxfound"] = False
        newstructuredContent.append(rr)
    return newstructuredContent


# finalStructureContent = newstructuredContent
distance2_cache = {}


def distance2(p1, p2):
    "Compute the distance squared, using cache."
    try:
        return distance2_cache[(p1, p2)]
    except KeyError:
        distance2_cache[(p1, p2)] = d2 = math.sqrt(
            (p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)
        return d2


def compressContent(finalStructureContent):

    compressedStructuredContent = []
    for idx, row in enumerate(finalStructureContent):
        if not row["matched"] and "strayText" not in row:
            if "strayText" in row:
                compressedStructuredContent.append(row)
            continue
        if row["isboxfound"]:
            logger.debug("pass %s", idx)
            continue
        if "matchedRow" in row and ("orphan" in row and row["orphan"]):
            x = row["matchedRow"]["bbox"][0]
            y = row["matchedRow"]["bbox"][1]

            maxImageDist = distance2(
                (0, 0), (row["matchedRow"]["imagesize"][0], row["matchedRow"]["imagesize"][1]))
            # lets find the closest box
            maxDist = 9999999
            closestBox = False
            closestIdx = False
            directionX = False
            directionY = False

            for idx2, row2 in enumerate(finalStructureContent):
                if idx2 <= idx:
                    continue

                if not row2["matched"] and "strayText" not in row2:
                    continue

                if "isboxfound" in row2 and row2["isboxfound"]:
                    continue

                if "matchedRow" in row2:
                    x2 = row2["matchedRow"]["bbox"][0]
                    y2 = row2["matchedRow"]["bbox"][1]
                    dist = distance2((x, y), (x2, y2))
                    if dist < maxDist:
                        maxDist = dist
                        closestIdx = idx2
                        closestBox = row2
                        if x2 > x:
                            directionX = "right"
                        else:
                            directionX = "left"

                        if y2 > y:
                            directionY = "down"
                        else:
                            directionY = "up"

            logger.debug("closest box found is for %s", row["line"])
            logger.debug(closestBox)
            logger.debug("distance %s", maxDist)
            logger.debug(directionX)
            logger.debug(directionY)
            percentDist = (maxDist/maxImageDist) * 100
            logger.debug("percentage of max distance %s", percentDist)
            if percentDist < 5:
                if directionY == "down":
                    logger.debug("%s should be prepeneded with %s",
                                 row["line"], closestBox["line"])

                    finalStructureContent[idx]["isboxfound"] = True
                    finalStructureContent[closestIdx]["isboxfound"] = True

                    logger.debug(closestIdx)
                    line = finalStructureContent[closestIdx]["line"]
                    newline = finalStructureContent[idx]["line"] + " " + line
                    finalStructureContent[idx]["line"] = newline

                    # del finalStructureContent[closestIdx]
                    if "append" not in finalStructureContent[idx]:
                        finalStructureContent[idx]["append"] = []

                    finalStructureContent[idx]["append"].append({
                        "type": "pre",
                        "row": copy.deepcopy(finalStructureContent[closestIdx])
                    })

                    compressedStructuredContent.append(
                        finalStructureContent[idx])

                else:
                    if "_Title_" in row["matchedRow"]["filename"]:
                        logger.debug(closestBox)
                        if "_Title_" in closestBox["matchedRow"]["filename"]:
                            pass
                        else:
                            logger.debug(
                                "this is a title field?? this cannot be appened? with non title %s", closestBox["matchedRow"]["filename"])
                            continue

                    logger.debug("%s should be appened with %s",
                                 row["line"], closestBox["line"])
                    finalStructureContent[idx]["isboxfound"] = True
                    finalStructureContent[closestIdx]["isboxfound"] = True

                    logger.debug(closestIdx)

                    line = finalStructureContent[closestIdx]["line"]
                    newline = line + " " + finalStructureContent[idx]["line"]
                    finalStructureContent[idx]["line"] = newline
                    # del finalStructureContent[closestIdx]
                    if "append" not in finalStructureContent[idx]:
                        finalStructureContent[idx]["append"] = []

                    finalStructureContent[idx]["append"].append({
                        "type": "append",
                        "row": copy.deepcopy(finalStructureContent[closestIdx])
                    })
                    compressedStructuredContent.append(
                        finalStructureContent[idx])
            else:
                logger.debug(
                    "will just ignore. not didnt find a box close enough for %s", row["line"])
                compressedStructuredContent.append(row)
        else:
            compressedStructuredContent.append(row)

    return compressedStructuredContent
