from app.detectron.start import test as startCVParsing
from app.picture.start import test as startPictureExtract
from app.ner.start import start as startNer

from app.logging import logger



def test_detectron():
    compressedStructuredContent = startCVParsing()
    assert len(compressedStructuredContent) > 0


def test_pic_extractor():
    files = startPictureExtract()
    assert len(files) > 0

    for f in files:

        if "92.pdf" in f["file"]:
            assert len(f["imageFile"]) > 0
        else:
            assert f["imageFile"] is False

def test_ner():
    entities = startNer(True)
    assert len(entities) > 0