from app.nerclassify.start import process as classifyNer
from app.ner.start import processAPI as extractNer
from app.detectron.start import processAPI
from app.picture.start import processAPI as extractPicture
from app.config import RESUME_UPLOAD_BUCKET, BASE_PATH, GOOGLE_BUCKET_URL
from app.logging import logger
from app.config import storage_client
from pathlib import Path
import subprocess
import os
# from app.search.index import addDoc
import shutil  


def fullResumeParsing(filename, mongoid=None):
    try:
        bucket = storage_client.bucket(RESUME_UPLOAD_BUCKET)
        blob = bucket.blob(filename)

        dest = BASE_PATH + "/../temp"
        Path(dest).mkdir(parents=True, exist_ok=True)
        filename, file_extension = os.path.splitext(filename)

        cvfilename = ''.join(
            e for e in filename if e.isalnum()) + file_extension
        cvdir = ''.join(e for e in cvfilename if e.isalnum())
        blob.download_to_filename(os.path.join(dest, cvfilename))

        filename = cvfilename

        logger.info("final file name %s", filename)

        if ".pdf" not in filename:
            inputFile = os.path.join(dest, filename)
            if len(file_extension.strip()) > 0:
                filename = filename.replace(file_extension, ".pdf")
            else:
                filename = filename + ".pdf"

            # libreoffice --headless --convert-to pdf /content/finalpdf/*.doc --outdir /content/finalpdf/
            x = subprocess.check_call(
                ['libreoffice --headless --convert-to pdf ' + inputFile + " --outdir  " + dest], shell=True)
            logger.info(x)

        fullResponse = {}

        response, basedir = extractPicture(os.path.join(dest, filename))

        fullResponse["picture"] = response

        if response:
            fullResponse["picture"] = fullResponse["picture"].replace(
                basedir + "/", GOOGLE_BUCKET_URL + cvdir + "/picture/")

        response, basePath = processAPI(os.path.join(dest, filename))

        finalLines = []
        for page in response:
            for pagerow in page["compressedStructuredContent"]:
                logger.info(pagerow)
                finalLines.append(pagerow["line"])

        # fullResponse["compressedContent"] = {"response" : response, "basePath" : basePath}

        nertoparse = []
        row = []
        for page in response:
            row.append(page["compressedStructuredContent"])

        nertoparse.append({"compressedStructuredContent": row})

        nerExtracted = extractNer(nertoparse)

        # fullResponse["nerExtracted"] = nerExtracted

        row = {}
        row["file"] = filename
        row["nerparsed"] = nerExtracted
        row["compressedStructuredContent"] = {}
        for pageIdx, page in enumerate(response):
            row["compressedStructuredContent"][str(
                pageIdx + 1)] = page["compressedStructuredContent"]

        combinData = classifyNer([row])[0]

        newCompressedStructuredContent = {}

        for pageno in combinData["compressedStructuredContent"].keys():
            pagerows = combinData["compressedStructuredContent"][pageno]
            newCompressedStructuredContent[pageno] = []
            for row in pagerows:
                if "classify" in row or True: #show all for now
                    # classify = row["classify"]
                    # if "append" in row:
                    #     del row["append"]
                    if "finalClaimedIdx" in row:
                        del row["finalClaimedIdx"]
                    if "isboxfound" in row:
                        del row["isboxfound"]
                    if "lineIdx" in row:
                        del row["lineIdx"]
                    if "matchedRow" in row:
                        if "bbox" in row["matchedRow"]:
                            del row["matchedRow"]["bbox"]
                        if "imagesize" in row["matchedRow"]:
                            del row["matchedRow"]["imagesize"]
                        if "matchRatio" in row["matchedRow"]:
                            del row["matchedRow"]["matchRatio"]

                        row["matchedRow"]["bucketurl"] = row["matchedRow"]["filename"].replace(
                            basePath + "/", GOOGLE_BUCKET_URL)

                    if "append" in row:
                        newAppend = []
                        for r in row["append"]:
                            if "row" in r:
                                if "finalClaimedIdx" in r["row"]:
                                    del r["row"]["finalClaimedIdx"]
                                if "isboxfound" in r["row"]:
                                    del r["row"]["isboxfound"]
                                if "lineIdx" in r["row"]:
                                    del r["row"]["lineIdx"]
                                if "matchedRow" in r["row"]:
                                    if "bbox" in r["row"]["matchedRow"]:
                                        del r["row"]["matchedRow"]["bbox"]
                                    if "idx" in r["row"]["matchedRow"]:
                                        del r["row"]["matchedRow"]["idx"]
                                    if "isClaimed" in r["row"]["matchedRow"]:
                                        del r["row"]["matchedRow"]["isClaimed"]
                                    if "imagesize" in r["row"]["matchedRow"]:
                                        del r["row"]["matchedRow"]["imagesize"]
                                    if "matchRatio" in r["row"]["matchedRow"]:
                                        del r["row"]["matchedRow"]["matchRatio"]

                                if "matchedRow" in r["row"]:
                                    r["row"]["matchedRow"]["bucketurl"] = r["row"]["matchedRow"]["filename"].replace(
                                        basePath + "/", GOOGLE_BUCKET_URL)

                            newAppend.append(r)

                        row["append"] = newAppend

                    newCompressedStructuredContent[pageno].append(row)

        combinData["newCompressedStructuredContent"] = newCompressedStructuredContent

        logger.info("full resume parsing completed %s", filename)
        ret = {
            "newCompressedStructuredContent": newCompressedStructuredContent,
            "finalEntity": combinData["finalEntity"],
            "picture": fullResponse["picture"]
        }

        # if mongoid:
        #     addDoc(mongoid, finalLines, ret)

        ret["debug"] = {
            "extractEntity": combinData["extractEntity"],
            "compressedStructuredContent": combinData["compressedStructuredContent"]
        }
        cvdir = ''.join(e for e in filename if e.isalnum())
        shutil.rmtree(BASE_PATH + "/../cvreconstruction/" + cvdir , ignore_errors = False) 
        logger.info("processing completed, final filename %s", filename)
        os.remove(BASE_PATH + "/../cvreconstruction/" + filename) 
        return ret

    except Exception as e:
        logger.info("error %s", str(e))
        return {
            "error": str(e)
        }
