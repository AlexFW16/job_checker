FROM node:20

RUN apt-get update && apt-get install -y git curl \
    && rm -rf /var/lib/apt/lists/* \
    && curl -fsSL https://opencode.ai/install | bash

WORKDIR /repo

ENV PATH="/usr/local/bin:${PATH}"
CMD ["/root/.opencode/bin/opencode"]
