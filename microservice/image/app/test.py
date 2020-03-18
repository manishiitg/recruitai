from image.start import start as saving_images

def test_imagessaving():
    compressedStructuredContent = saving_images()
    assert compressedStructuredContent != 0    
