from bs4 import BeautifulSoup

def cleanMe(html):
    # create a new bs4 object from the html data loaded
    
    # print(html)
    soup = BeautifulSoup(html, "html.parser")
    # remove all javascript and stylesheet code
    for script in soup(["script", "style"]):
        script.extract()
    # get text
    text = soup.get_text(separator=' ')

    # break into lines and remove leading and trailing space on each
    # lines = (line.strip() for line in text.splitlines())
    lines = text.splitlines()
    # break multi-headlines into a line each
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    # drop blank lines
    # text = '\n'.join(chunk for chunk in chunks if chunk)
    chunks = filter(None, chunks)
    return " ".join(chunks)