from app.image.start import test_pdfToimage 
from app.image.start import test_docToimage 

def test_pdfToimagessaving():
    imageContent = test_pdfToimage()
    assert imageContent != 0  

def test_docToimagessaving():
    imageContent = test_docToimage()
    assert imageContent != 0  
