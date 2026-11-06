FROM alpine:3.20

RUN apk add --no-cache tinyproxy
COPY tinyproxy.conf /etc/tinyproxy/tinyproxy.conf
COPY dominios-permitidos /etc/tinyproxy/dominios-permitidos

USER tinyproxy
ENTRYPOINT ["tinyproxy", "-d", "-c", "/etc/tinyproxy/tinyproxy.conf"]
