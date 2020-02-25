from app.skillsword2vec.start import test as teststartSkill
from app.emailclassify.start import test as testEmailClassifyFunc


from app.logging import logger


def testEmailClassify():
    data = testEmailClassifyFunc()
    assert list(data[0]["ai"]["pipe1"].keys())[0] == "candidate"

def testwork2vecskill():
    logger.info("word2vec skills testing.....")
    resp = teststartSkill()
    assert isinstance(resp, list)


