import logging
import flair
import torch
from flair.models import SequenceTagger
from app.logging import logger
from app.config import BASE_PATH
import json
from app import mongo
import torch
from tqdm import tqdm_notebook as tqdm
from flair.data import Sentence

device = None
if torch.cuda.is_available():
    device = torch.device('cuda:0')
else:
    device = torch.device('cpu')

logger.info(device)

flair.device = device


def start(isTesting=False):
    tagger = loadModel()

    if isTesting:
        logger.setLevel(logging.INFO)
        logger.info("device available %s", device)
        sents = getFilesToParseForTesting()

        entities = []
        for sent in sents:
            sentence = Sentence(sent)

            # predict tags and print
            tagger.predict(sentence)

            logger.info(sentence.to_tagged_string())

            for entity in sentence.get_spans('ner'):
                logger.info(entity)
                entities.append(entity)

        return entities
    else:
        logger.setLevel(logging.CRITICAL)
        nertoparse = getFilesToParseFromDB()

        return process(nertoparse, tagger)


def loadModel():
    logger.info("loading model")
    tagger = SequenceTagger.load(
        BASE_PATH + "/../pretrained/recruit-ner-flair-augment/best-model.pt")
    logger.info("model loaded")
    return tagger


def process(nertoparse, tagger):
    for idx in tqdm(range(len(nertoparse))):
        row = nertoparse[idx]
        compressedStructuredContent = row["compressedStructuredContent"]

        finalNER = []
        for r in compressedStructuredContent:
            lines = nerlines(r)
            ner = []
            for lineData in lines:
                line = lineData["line"]
                line = bytes(line, 'utf-8').decode('ascii', 'ignore')
                line = line.strip()
                logger.info(line)
                if len(line) > 0:
                    if "contentIdx" not in lineData:
                        lineData["contentIdx"] = []

                        contentIdx = lineData["contentIdx"]
                        sentence = Sentence(line)
                        # predict tags and print
                        tagger.predict(sentence)
                        logger.info(sentence.to_tagged_string())
                        for entity in sentence.get_spans('ner'):
                            logger.info(entity)

                        ner.append({
                            "line": line,
                            "nerline": str(sentence.to_tagged_string()),
                            "entity": sentence.to_dict(tag_type='ner'),
                            "lineData": lineData,
                            "contentIdx": contentIdx
                        })

                finalNER.append(ner)

        row["finalner"] = finalNER

        mongo.db.cvparsingsample.update_one({
            "_id": row["_id"]
        }, {"$set": {
            "nerparsed": finalNER,
            "nerparsedv3": True
        }})


def getFilesToParseForTesting():
    sents = [
        "Rebekah Sabarwal Phone +91 82888-23431 Email rebekahsabarwal1919@gmail.com Experienced as a Team Leader and Sales Officer in FMCG with a well grounded history of working in Retail industry. Skilled in the In-Store Execution, Sales, Marketing, Operations and OJT. Achieved Excellence in Sales, Outdoor & In-store Promotions and Business Development.",
        "PROFESSIONAL EXPERIENCE Five Year of Working Experience in Retail & Sales. Handling Upper North like J&K, Punjab ,U.T ,delhi - NCR and Haryana. In Five Years of my Professional Career I have worked for Several Top Ranked Companies Like- L’OREAL, ORIGANIC, and HFS. Following are the descriptions of job in which I have contributed for Business Development, Management, Sales, Training & Recruitment.",
        "Project:1 Designation Organization Descriptions Period : : : : Team Leader & Training Coach L’Oreal India PVT. LTD., North India L’Oreal ISP Project{Entire Upper North} Dec 2016 to Till date",
        "Roles & Responsibilities",
        " Dealing with a huge team of 45 sales representatives.  Setting goals for performance and deadlines in ways that comply with company’s plans, Vision & sales.  PJP Adherence  Man Days Utilization  Ensuring Team’s Discipline & code of conduct- Timely login & reporting.  Competition Intelligence: Visibility/Promos/New Launches.  OJT of ISP during every visit, Assisting ISP in their learning, leading by examples and Motivating team to meet and exceed goals..  Contacting potential clients via email or phone to establish rapport and set up meetings  Communicating clear instructions to Sales Representatives.  Managing complete sales operations of the sales team.  Attending conferences, meetings, and industry events  Preparing PowerPoint & Excel presentations and sales displays  Able to provide quality leadership to a large team of sales people in order to ensuring their effectiveness & productivity.  Making various Incentives Schemes for Representatives.  Monitoring Promoters productivity and providing constructive feedback  Maintain inventory and ensure items are in stock.  Collecting Team Performance Follow-up for Target Achievement, Grooming & Hygiene standards.  Maintaining Relationship with Store Staffs’  Maintain inventory and ensure items are in stock.  Assisting sales representatives and Motivating team to meet and exceed goals.  Communicating clear instructions to Sales Representatives.  Dealing with multiple parties (Distributors & 40+ Candidates)."
        "Previous Employer - Novo Nordisk . Experience - November 2015- March 2017 Work as Marketing Executive. Job Profile",
        " Making presentations to Doctors. Keeping up-to-date with the latest clinical data supplied by the company, and interpreting, presenting and discussing this data with health professionals during presentations regarding insulin and diabetes  Meeting Monthly, Quarterly and Annual Sales Targets.  Planning work schedules, Weekly and Monthly timetables.  Attending company meetings, technical data presentations and briefings.  Monitoring competitor activity and competitors' products. Achievement –  Achieving Secondary Sales data from January till March,17.  Upgradation of insulin Actrapid to insulin Novorapid in ICU at Hirananadani Hospital.  Conducting continuous medical education program for doctors in the Hospitals.",
        "Projects undertaken:  Name of the company: Brandcare Medical Advertising & Consultancy Pvt.  Title of the project: Usage of Digital Marketing in India.  Objective: To study perception of brand managers on usage of digital marketing in pharmaceutical industry in India.  Name of the company: Brandcare Medical Advertising & Consultancy Pvt.  Title of the project: Usage of Digital Marketing in India.  Objective: To study perception of brand managers on usage of digital marketing in pharmaceutical industry in India.",
        "EDUCATIONAL QUALIFICATION:  Post Graduate Diploma in Pharmaceutical Marketing ( 2014-2016)  Completed Post graduation Diploma in Clinical Research  Bachelor of Science in Chemistry  Post Graduate Diploma in Pharmaceutical Marketing ( 2014-2016)  Completed Post graduation Diploma in Clinical Research  Bachelor of Science in Chemistry"
    ]
    return sents


def getFilesToParseFromDB():
    ret = mongo.db.cvparsingsample.find(
        {"nerparsedv3": {"$exists": False}, "parsed": True})
    nertoparse = []
    for row in ret:
        row["compressedStructuredContent"] = []
        for cvpage in range(1, 10):
            # max 10 cv pages
            cvpage = str(cvpage)
            if cvpage in row and "compressedStructuredContent" in row[cvpage]:
                row["compressedStructuredContent"].append(
                    json.loads(row[cvpage]["compressedStructuredContent"]))
            else:
                break

            nertoparse.append(row)

    return nertoparse


def nerlines(compressedStructuredContent):
    # prepare for ner
    nerlines = []

    for row in compressedStructuredContent:
        row["line"] = row["line"].strip()
        nerlines.append(row)

    MINNERLINELEN = 8

    prepend = False

    for idx, nerrow in enumerate(nerlines):
        if len(nerrow["line"].split(" ")) <= MINNERLINELEN and idx == 0:
            logger.debug(
                "this is first line... and its short then need to prepend to next line")
            prepend = True

            continue

        if len(nerrow["line"].split(" ")) <= MINNERLINELEN and len(nerlines) > 0 and len(nerrow["line"]) > 0:

            logger.debug("short line %s", nerrow["line"])

            if len(nerlines[idx-1]["line"].split(" ")) >= MINNERLINELEN:
                logger.debug("prev line is big %s", nerlines[idx-1]["line"])
                nerlines[idx]["contentIdx"] = [idx]
            else:
                nerlines[idx-1]["line"] = nerlines[idx -
                                                   1]["line"] + " " + nerrow["line"]
                # nerlines[-1]["istype"] = "nerappend"
                nerlines[idx]["line"] = ""
                nerlines[idx]["contentIdx"] = []
                if "contentIdx" not in nerlines[idx-1]:
                    nerlines[idx-1]["contentIdx"] = []

                nerlines[idx-1]["contentIdx"].extend([idx-1, idx])
                nerlines[idx -
                         1]["contentIdx"] = list(set(nerlines[idx-1]["contentIdx"]))

        else:
            nerlines[idx]["contentIdx"] = [idx]

        if prepend:
            nerlines[idx]["line"] = nerlines[idx-1]["line"] + \
                " " + nerlines[idx]["line"]
            nerlines[idx-1]["line"] = ""
            nerlines[idx]["contentIdx"] = [idx-1, idx]
            prepend = False

        else:
            pass

    logger.debug("===============================")
    logger.debug("===============================")
    logger.debug("===============================")
    for row in nerlines:
        logger.debug(row["line"])

    return nerlines
