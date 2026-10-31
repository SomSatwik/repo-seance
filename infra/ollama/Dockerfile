FROM ollama/ollama:latest

COPY infra/ollama/start.sh /usr/local/bin/ollama-render-start
RUN chmod +x /usr/local/bin/ollama-render-start

ENV OLLAMA_MODELS=/var/lib/ollama

EXPOSE 11434

ENTRYPOINT ["/usr/local/bin/ollama-render-start"]
