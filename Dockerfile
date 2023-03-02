############################################################
# Dockerfile to build Tracking Code Manager
############################################################
#sudo docker build -t tracking-code-manager .
#sudo docker run -p 10031:10031 -i -t tracking-code-manager
###########################################################################

FROM python:3.8.1

# File Author / Maintainer
MAINTAINER "Taylor Hanson <tahanson@cisco.com>"

# Copy the application folder inside the container
ADD . .

# Set the default directory where CMD will execute
WORKDIR /

# Get pip to download and install requirements:
RUN pip install python-dotenv
RUN pip install tornado==4.5.2

#Copy environment variables file. Overwrite it with prod.env if prod.env exists.
COPY .env prod.env* .env


# Set the default command to execute
# when creating a new container
CMD ["python","-u","server.py"]
