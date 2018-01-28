FROM selenium/standalone-firefox
COPY . ./server
RUN sudo apt-get update
RUN sudo apt-get install python3 python3-pip -y
RUN sudo apt-get install tesseract-ocr -y
RUN pip3 install -r ./server/requirements.txt
