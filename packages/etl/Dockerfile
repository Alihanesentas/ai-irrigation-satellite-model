FROM python:3.12-slim

# GDAL/GEOS runtime libs are required by rioxarray, geopandas, odc-stac.
RUN apt-get update && apt-get install -y --no-install-recommends \
    gdal-bin \
    libgdal-dev \
    libgeos-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/dagster/app

# Path dependency on packages/core: copy it in alongside this package so a
# plain `pip install .` resolves it, matching pyproject.toml's
# [tool.uv.sources] agritwin-core = { path = "../core" }.
COPY packages/core /opt/dagster/packages/core
COPY packages/etl /opt/dagster/app

RUN pip install --no-cache-dir /opt/dagster/packages/core \
    && pip install --no-cache-dir .

ENV DAGSTER_HOME=/opt/dagster/dagster_home
RUN mkdir -p "$DAGSTER_HOME"

EXPOSE 3000

# No CMD/ENTRYPOINT here on purpose — docker-compose.yml sets the command
# (dagster-webserver vs dagster-daemon) so both services share this one image.
