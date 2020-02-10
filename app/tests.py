from app.detectron.start import start as startCVParsing
from app.picture.start import start as startPictureExtract
from app.ner.start import start as startNer
from app.skillsword2vec.start import start as startSkill

from app.logging import logger

def testwork2vecskill():
    logger.info("word2vec skills testing.....")
    resp = startSkill(True)
    # logger.info(resp)
    assert isinstance(resp, list)


# def test_ner():
#     entities = startNer(True)
#     assert len(entities) > 0

# def test_detectron():
#     compressedStructuredContent = startCVParsing(True)
#     assert len(compressedStructuredContent) > 0


# def test_pic_extractor():
#     files = startPictureExtract(True)
#     assert len(files) > 0

#     for f in files:

#         if "92.pdf" in f["file"]:
#             assert len(f["imageFile"]) > 0
#         else:
#             assert f["imageFile"] is False
