# base image
FROM python:3.10-alpine

# copy entire directory into container
COPY . /app/dcm-object-validator
# copy accessories
COPY ./app.py /app/app.py

# set working directory
WORKDIR /app

# install the package deps
# java
RUN apk add openjdk17
# jhove
RUN mkdir /app/jhove
WORKDIR /app/jhove
RUN wget -Y on -O jhove-latest.jar "http://software.openpreservation.org/rel/jhove-latest.jar" && \
    echo '<?xml version="1.0" encoding="UTF-8" standalone="no"?><AutomatedInstallation langpack="eng"><com.izforge.izpack.panels.htmlinfo.HTMLInfoPanel id="welcome"/><com.izforge.izpack.panels.target.TargetPanel id="install_dir"><installpath>'/app/jhove/'</installpath></com.izforge.izpack.panels.target.TargetPanel><com.izforge.izpack.panels.packs.PacksPanel id="sdk_pack_select"><pack index="0" name="JHOVE Application" selected="true"/><pack index="1" name="JHOVE Shell Scripts" selected="true"/><pack index="2" name="JHOVE External Modules" selected="true"/></com.izforge.izpack.panels.packs.PacksPanel><com.izforge.izpack.panels.install.InstallPanel id="install"/><com.izforge.izpack.panels.finish.FinishPanel id="finish"/></AutomatedInstallation>' > jhove-auto-install.xml && \
    java -jar jhove-latest.jar jhove-auto-install.xml && \
    rm jhove-auto-install.xml jhove-latest.jar
ENV JHOVE_APP=/app/jhove/jhove

#
WORKDIR /app

# python
RUN --mount=type=secret,id=zivgitlab,target=/root/.netrc \
    pip install --upgrade \
    --extra-index-url https://zivgitlab.uni-muenster.de/api/v4/groups/12466/-/packages/pypi/simple \
    "dcm-object-validator/[cors]"
RUN rm -r dcm-object-validator/
ENV ALLOW_CORS=1
# and wsgi server (gunicorn)
RUN pip install gunicorn

# run and expose to local network(machine)
ENTRYPOINT [ "gunicorn" ]
CMD ["--bind", "0.0.0.0:8080", "app:app"]
