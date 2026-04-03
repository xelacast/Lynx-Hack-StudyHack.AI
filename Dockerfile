FROM docker.n8n.io/n8nio/n8n:latest

USER root

# 1. Restore the 'apk' package manager via Alpine's official static binary
RUN arch=$(uname -m) && \
    wget -qO /sbin/apk https://gitlab.alpinelinux.org/api/v4/projects/5/packages/generic/v2.14.4/$arch/apk.static && \
    chmod +x /sbin/apk

# Install Python and pip
RUN apk add --update --no-cache python3 py3-pip

USER node