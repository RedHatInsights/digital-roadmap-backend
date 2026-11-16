FROM registry.access.redhat.com/ubi10-minimal:10.2-1784669047 AS base

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
RUN "python${PYTHON_VERSION}" -m venv "$VENV" \
    && "$PYTHON" -m pip install --no-cache-dir --upgrade pip \
    && "$PYTHON" -m pip install --no-cache-dir --requirement /usr/share/container-setup/requirements.txt


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
ADD /src/notificator /srv/roady/notificator/
ADD uvicorn_disable_logging.json /srv/roady/uvicorn_disable_logging.json

ADD scripts/.release /srv/roady/
ADD --chmod=0644 \
    https://gitlab.cee.redhat.com/rhel-lightspeed/roadmap/data/-/raw/main/data/roadmap_jira.json \
    /srv/roady/roadmap/data/upcoming.json

USER roady
WORKDIR /srv/roady

# Which peers uvicorn believes when it takes the client address from
# X-Forwarded-For. It does not control who may send that header -- anyone can.
# Uvicorn reads this variable only when --forwarded-allow-ips is absent from
# the command line, so the flag must stay off for the deployment to be able to
# override it.
#
# "*" trusts any peer, which is what the hardcoded flag did before. It is kept
# as the image default so behaviour does not change on upgrade, and so the
# image still works outside OpenShift. Narrow it per environment by setting
# FORWARDED_ALLOW_IPS on the deployment to the router's address range; a
# comma separated list of addresses or CIDR blocks is accepted.
#
# What this does and does not control: uvicorn uses the list only to decide
# whether to rewrite scope["client"] from X-Forwarded-For. It does not strip
# the headers, and roadmap.audit.client_network reads them directly, so
# narrowing the list does not stop a peer that can reach the pod from setting
# src_ip. It fixes peer_ip, and the value src_ip falls back to when no
# forwarding header is present. See docs/SECURITY_LOGGING.md.
#
# Three distinct states, which are easy to confuse:
#   absent  -> uvicorn defaults to 127.0.0.1,::1 and stops trusting the router
#   empty   -> no peer is trusted at all, including the router
#   "*"     -> every peer is trusted
# The ENV line exists so the first case cannot happen by accident.
ENV FORWARDED_ALLOW_IPS="*"

CMD ["uvicorn", "roadmap.main:app", "--proxy-headers", "--port", "8000", "--host", "0.0.0.0", "--log-config", "uvicorn_disable_logging.json"]
