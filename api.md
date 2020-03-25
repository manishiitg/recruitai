===

Api end point exposed 

http://176.9.137.77:8085/skill/reactjs+php+html-jquery
(to get similar skills or negative skils + means similar skills and - means negative skills)


http://176.9.137.77:8085/emailclassify/i%20want%20to%20apply%20for%20a%20job%20as%20react%20developer/job%20application
(this to classify email as candidate or general)

http://176.9.137.77:8085/emailclassify/get%20studio%20benfies%20%20asdf%20asfa%20sdfasd%20fasdf%20asdfasd%20fasdf%20asfd%20sdf%20s/agency

####### need to work on this classifier more ###############
e.g
http://176.9.137.77:8085/emailclassify/get%20studio%20benfies%20%20asdf%20asfa%20sdfasd%20fasdf%20asdfasd%20fasdf%20asfd%20sdf%20s/thomas

returns
[
  {
    "ai": {
      "pipe1": {
        "other": 0.9968185424804688
      }
    }, 
    "body": "get studio benfies  asdf asfa sdfasd fasdf asdfasd fasdf asfd sdf s", 
    "subject": "thomas"
  }
]


http://176.9.137.77:8085/emailclassify/get%20studio%20benfies%20%20asdf%20asfa%20sdfasd%20fasdf%20asdfasd%20fasdf%20asfd%20sdf%20s/hello

[
  {
    "ai": {
      "pipe1": {
        "candidate": 0.9458337426185608
      }
    }, 
    "body": "get studio benfies  asdf asfa sdfasd fasdf asdfasd fasdf asfd sdf s", 
    "subject": "hello"
  }
]

so just the word "hello" has to be learnt as candidate. this is not correct.....




http://176.9.137.77:8086/resume/picture/102.pdf
get picture of candidate from resume


http://176.9.137.77:8086/resume/102.pdf/123

full parsing of a resume, getting all ner data and classiifcation and images



http://144.76.110.170:8086/gender/manish

returns gender for a name


http://144.76.110.170:8086/classify/candidate/5e65d5b6904e4a548c9755a0

to classify candidate globally and get his skills



http://144.76.110.170:8086/datasync/filter/fetch/0/full_data