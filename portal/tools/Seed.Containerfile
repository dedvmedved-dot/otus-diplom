# Minimal private-seed artifact. NOT the Portal binary, NOT deployable, no secrets.
# Used only to establish the private package + repository association before the
# main release's private-before check. Bootstrap-only; never an accepted app image.
FROM scratch
LABEL org.opencontainers.image.title="otus-diplom-portal-seed" \
      org.opencontainers.image.description="bootstrap-only seed, not deployable" \
      org.opencontainers.image.source="https://github.com/dedvmedved-dot/otus-diplom"
COPY seed.txt /seed.txt
