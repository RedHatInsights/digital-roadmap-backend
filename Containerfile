FROM registry.access.redhat.com/ubi9-minimal:latest AS builder

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

ENV VENV=/opt/venvs/rhel_roadmap
ENV PYTHON="${VENV}/bin/python"
ENV PATH="${VENV}/bin:$PATH"
ENV PYTHON_VERSION="3.12"

RUN microdnf install -y --nodocs \
    gcc \
    libpq-devel \
    "python${PYTHON_VERSION}" \
    "python${PYTHON_VERSION}-devel" \
    && rm -rf /var/cache/yum/*

COPY "requirements/requirements-${PYTHON_VERSION}.txt" /usr/share/container-setup/requirements.txt
RUN "python${PYTHON_VERSION}" -m venv "$VENV" \
    && "$PYTHON" -m pip install --no-cache-dir --upgrade pip setuptools \
    && "$PYTHON" -m pip install --no-cache-dir --requirement /usr/share/container-setup/requirements.txt


FROM registry.access.redhat.com/ubi9-minimal:latest AS final

ENV VENV=/opt/venvs/rhel_roadmap
ENV PYTHON="${VENV}/bin/python"
ENV PATH="${VENV}/bin:$PATH"
ENV PYTHON_VERSION="3.12"

COPY LICENSE /licenses/Apache-2.0.txt
COPY --from=builder "${VENV}" "${VENV}"

RUN microdnf install -y --nodocs \
    libpq \
    "python${PYTHON_VERSION}" \
    && rm -rf /var/cache/yum/*

COPY /src/roadmap/ /srv/rhel_roadmap/roadmap/

RUN useradd --system --create-home --home-dir /srv/rhel_roadmap roady

USER roady
WORKDIR /srv/rhel_roadmap

CMD ["fastapi", "run", "roadmap/main.py", "--proxy-headers", "--port", "80"]
