# Building the main container
FROM python:3.7-slim

WORKDIR /label-studio

RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y git

RUN git clone https://github.com/heartexlabs/label-studio.git .

# Copy and install requirements.txt first for caching
# COPY requirements.txt /label-studio
RUN pip install -r requirements.txt

ENV PORT="8200"
ENV collect_analytics=0
EXPOSE ${PORT}

RUN pip install -e .

VOLUME [ "/label-studio/classify" ]

CMD ["label-studio", "start", "classify"]

