FROM ubuntu:18.04

RUN apt-get update \
	&& apt-get -y upgrade \
	&& apt-get install -y python3 \
	&& apt-get install -y python3-pip \
	&& apt-get install -y libssl-dev \
	&& apt-get install -y zlib1g-dev \
	&& apt-get install -y curl \
	&& apt-get install -y wget

RUN mkdir /code
WORKDIR /code
COPY . .
RUN pip3 install -r requirements.txt

EXPOSE 8000
#RUN python3 manage.py makemigrations services
#RUN python3 manage.py migrate

#CMD ['python3', 'manage.py', 'runserver', '0.0.0.0:8000']
