# Copyright (c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>
# SPDX-License-Identifier: LGPL-3.0-or-later
#
# MkDocs with Material theme for building documentation
FROM python:3.11-slim

LABEL maintainer="Eduardo Correia <ecorreia@apliant.com.br>"
LABEL description="Documentation builder for Bake Linter"

# Install MkDocs with Material theme (modern ReadTheDocs-style theme)
# Let pip resolve compatible versions
RUN pip install --no-cache-dir \
    mkdocs-material \
    pygments

WORKDIR /docs

# Expose port for live server (optional, for development)
EXPOSE 8001

# Default command: build the documentation
CMD ["mkdocs", "build", "--config-file", "mkdocs.yml", "--strict"]
