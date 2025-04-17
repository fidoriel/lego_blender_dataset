FROM python:3.13

RUN apt-get update -y; apt-get install wget unzip -y

RUN mkdir /renderer
WORKDIR /renderer

RUN https://library.ldraw.org/library/updates/complete.zip && \
    unzip complete.zip && \
    rm complete.zip


RUN wget https://github.com/TobyLobster/ImportLDraw/releases/download/v1.2.1/importldraw1.2.1.zip
RUN pip install blenderproc
RUN python3 -c "import blenderproc as bproc; bproc.init()"