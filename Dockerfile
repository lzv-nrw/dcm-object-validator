FROM python:3.10-alpine

# setup for all users
RUN umask 022

# install java dependencies
# java
RUN apk add openjdk17
# jhove
RUN mkdir -p /app/jhove
WORKDIR /app/jhove
RUN wget -Y on -O jhove.jar "https://software.openpreservation.org/releases/jhove/jhove-1.32.jar" && \
    echo "1cde66c3fe669e5a93f41378e944bf7a  jhove.jar" | md5sum -c - && \
    echo '<?xml version="1.0" encoding="UTF-8" standalone="no"?><AutomatedInstallation langpack="eng"><com.izforge.izpack.panels.htmlinfo.HTMLInfoPanel id="welcome"/><com.izforge.izpack.panels.target.TargetPanel id="install_dir"><installpath>'/app/jhove/'</installpath></com.izforge.izpack.panels.target.TargetPanel><com.izforge.izpack.panels.packs.PacksPanel id="sdk_pack_select"><pack index="0" name="JHOVE Application" selected="true"/><pack index="1" name="JHOVE Shell Scripts" selected="true"/><pack index="2" name="JHOVE External Modules" selected="true"/></com.izforge.izpack.panels.packs.PacksPanel><com.izforge.izpack.panels.install.InstallPanel id="install"/><com.izforge.izpack.panels.finish.FinishPanel id="finish"/></AutomatedInstallation>' > jhove-auto-install.xml && \
    java -jar jhove.jar jhove-auto-install.xml && \
    rm jhove-auto-install.xml jhove.jar
ENV DEFAULT_JHOVE_CMD=/app/jhove/jhove

# set working directory
WORKDIR /app

# copy entire directory into container
COPY ./ /app/dcm-object-validator
# move AppConfig
RUN mv /app/dcm-object-validator/app.py /app/app.py

# install app package
RUN pip install --upgrade \
    --extra-index-url https://zivgitlab.uni-muenster.de/api/v4/projects/9020/packages/pypi/simple \
    "/app/dcm-object-validator/[cors, fido]"
RUN rm -r /app/dcm-object-validator/

# install wsgi server
RUN pip install gunicorn

# add and set default user
RUN adduser -u 303 -S dcm -G users
RUN mkdir -p /file_storage && chown -R dcm:users /file_storage && chmod -R +w /file_storage
USER dcm

# define startup
ENV WEB_CONCURRENCY=5
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:80 --workers 1 --threads ${WEB_CONCURRENCY} app:app"]
