FROM registry.access.redhat.com/ubi10-minimal:10.0-1755721767 AS base

FROM base AS builder

ENV VENV=/opt/venvs/roadmap
ENV PYTHON="${VENV}/bin/python"
ENV PATH="${VENV}/bin:$PATH"
ENV PYTHON_VERSION="3.12"

RUN microdnf install -y --nodocs \
    gcc \
    libpq-devel \
    "python${PYTHON_VERSION}" \
    python3-devel \
    && rm -rf /var/cache/yum/*

ADD "requirements/requirements-${PYTHON_VERSION}.txt" /usr/share/container-setup/requirements.txt
ADD "requirements/requirements-replication-${PYTHON_VERSION}.txt" /usr/share/container-setup/requirements-replication.txt
RUN "python${PYTHON_VERSION}" -m venv "$VENV" \
    && "$PYTHON" -m pip install --no-cache-dir --upgrade pip \
    && "$PYTHON" -m pip install --no-cache-dir --requirement /usr/share/container-setup/requirements.txt \
    # Inventory sync venv setup
    && "python${PYTHON_VERSION}" -m venv /opt/venvs/replication \
    && "$PYTHON" -m pip install --no-cache-dir --upgrade pip \
    && /opt/venvs/replication/bin/python -m pip install --no-cache-dir --requirement /usr/share/container-setup/requirements-replication.txt


FROM base AS final

ARG SOURCE_DATE_EPOCH

LABEL com.redhat.component=insights-planning-api
LABEL cpe="cpe:2.3:a:redhat:insights_planning:-:*:*:*:*:*:*:*"
LABEL description="Red Hat Enterprise Linux Roadmap API"
LABEL distribution-scope=private
LABEL io.k8s.description="Insights for RHEL Planning API"
LABEL io.k8s.display-name="Insights for RHEL Planning API"
LABEL io.openshift.tags="rhel,insights,roadmap"
LABEL name=insights-planning-api
LABEL org.opencontainers.image.created=${SOURCE_DATE_EPOCH}
LABEL release=0.0.1
LABEL summary="Red Hat Enterprise Linux Roadmap API"
LABEL url="https://github.com/RedHatInsights/digital-roadmap-backend"
LABEL vendor="Red Hat, Inc."
LABEL version=0.0.1

ENV VENV=/opt/venvs/roadmap
ENV PYTHON="${VENV}/bin/python"
ENV PATH="${VENV}/bin:$PATH"
ENV PYTHON_VERSION="3.12"
ENV PYTHONPATH=/srv/roady/

ADD LICENSE /licenses/Apache-2.0.txt
COPY --from=builder /opt/venvs/ /opt/venvs/

RUN microdnf install -y --nodocs \
    libpq \
    "python${PYTHON_VERSION}" \
    && rm -rf /var/cache/yum/*

RUN useradd --key HOME_MODE=0755 --system --create-home --home-dir /srv/roady roady

ADD /src/roadmap/ /srv/roady/roadmap/
COPY uvicorn_disable_logging.son /srv/roady/uvicorn_disable_logging.json
ADD /scripts/replication.py /usr/local/bin/replication.py

ADD scripts/.release /srv/roady/
ADD --chmod=0644 \
    https://gitlab.cee.redhat.com/rhel-lightspeed/roadmap/data/-/raw/main/data/roadmap_jira.json \
    /srv/roady/roadmap/data/upcoming.json

USER roady
WORKDIR /srv/roady

CMD ["uvicorn", "roadmap.main:app", "--proxy-headers", "--forwarded-allow-ips=*", "--port", "8000", "--host", "0.0.0.0", "--log-config", "uvicorn_disable_logging.json"]
