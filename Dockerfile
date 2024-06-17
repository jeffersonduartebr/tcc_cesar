FROM python:3.10.10

WORKDIR /app/tcc_cesar/

RUN apt update -y 
RUN apt install -y git python3-pip gcc python3-dev wget
RUN wget https://r.mariadb.com/downloads/mariadb_repo_setup
RUN chmod +x mariadb_repo_setup
RUN ./mariadb_repo_setup --mariadb-server-version="mariadb-10.6"
RUN apt update -y
RUN apt install -y libmariadb3 libmariadb-dev
RUN pip3 install dash cachetools dask dask[dataframe] plotly mariadb swifter matplotlib dask[distributed] --quiet

EXPOSE 8050


