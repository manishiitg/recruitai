from app.detectron.start import test as startCVParsing
from app.picture.start import test as startPictureExtract
from app.ner.start import start as startNer
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


# def test_ner():
#     entities = startNer(True)
#     assert len(entities) > 0

# def test_detectron():
#     compressedStructuredContent = startCVParsing()
#     assert len(compressedStructuredContent) > 0


# def test_pic_extractor():
#     files = startPictureExtract(True)
#     assert len(files) > 0

#     for f in files:

#         if "92.pdf" in f["file"]:
#             assert len(f["imageFile"]) > 0
#         else:
#             assert f["imageFile"] is False
