FROM bcgovimages/von-image:py36-1.16-1

ENV ENABLE_PTVSD 0

RUN pip3 install --no-cache-dir 'python3-indy>=1.11.1<2'

RUN mkdir mount && chown -R indy:indy mount && chmod -R ug+rw mount
ADD did-recovery.py ./

VOLUME /home/indy/mount

ENTRYPOINT ["/bin/bash", "-c", "python3 did-recovery.py \"$@\"", "--"]
