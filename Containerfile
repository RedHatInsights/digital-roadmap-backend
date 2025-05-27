FROM registry.access.redhat.com/ubi10-minimal:latest AS builder

LABEL com.redhat.component=rhel-roadmap-api
LABEL description="Red Hat Enterprise Linux Roadmap API"
LABEL distribution-scope=private
LABEL io.k8s.description="Red Hat Enterprise Linux Roadmap API"
LABEL io.k8s.display-name="RHEL Roadmap API"
LABEL io.openshift.tags="rhel,lightspeed,roadmap"
LABEL name=rhel-roadmap-api
LABEL release=0.0.1
LABEL summary="Red Hat Enterprise Linux Roadmap API"
LABEL url="https://github.com/RedHatInsights/digital-roadmap-backend"
LABEL vendor="Red Hat, Inc."
LABEL version=0.0.1

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

COPY "requirements/requirements-${PYTHON_VERSION}.txt" /usr/share/container-setup/requirements.txt
COPY "requirements/requirements-replication-${PYTHON_VERSION}.txt" /usr/share/container-setup/requirements-replication.txt
RUN "python${PYTHON_VERSION}" -m venv "$VENV" \
    && "$PYTHON" -m pip install --no-cache-dir --upgrade pip setuptools \
    && "$PYTHON" -m pip install --no-cache-dir --requirement /usr/share/container-setup/requirements.txt \
    # Inventory sync venv setup
    && "python${PYTHON_VERSION}" -m venv /opt/venvs/replication \
    && "$PYTHON" -m pip install --no-cache-dir --upgrade pip setuptools \
    && /opt/venvs/replication/bin/python -m pip install --no-cache-dir --requirement /usr/share/container-setup/requirements-replication.txt


FROM registry.access.redhat.com/ubi10-minimal:latest AS final

ENV VENV=/opt/venvs/roadmap
ENV PYTHON="${VENV}/bin/python"
ENV PATH="${VENV}/bin:$PATH"
ENV PYTHON_VERSION="3.12"
ENV PYTHONPATH=/srv/roady/

COPY LICENSE /licenses/Apache-2.0.txt
COPY --from=builder /opt/venvs/ /opt/venvs/

RUN microdnf install -y --nodocs \
    libpq \
    "python${PYTHON_VERSION}" \
    && rm -rf /var/cache/yum/*

RUN useradd --key HOME_MODE=0755 --system --create-home --home-dir /srv/roady roady

COPY /src/roadmap/ /srv/roady/roadmap/
COPY /scripts/replication.py /usr/local/bin/replication.py

RUN curl \
    --insecure \
    --fail \
    --output /srv/roady/roadmap/data/upcoming.json \
    "https://gitlab.cee.redhat.com/api/v4/projects/107966/repository/files/data%2F02_roadmap_jira.json/raw?ref=main"

USER roady
WORKDIR /srv/roady

CMD ["uvicorn", "roadmap.main:app", "--proxy-headers", "--forwarded-allow-ips=*", "--port", "8000", "--host", "0.0.0.0"]
