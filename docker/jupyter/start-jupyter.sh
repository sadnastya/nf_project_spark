#!/bin/bash
# Контейнер запускается под UID хоста (чтобы ноутбуки сохранялись с правильным владельцем).
# Java/Hadoop требуют имя пользователя — регистрируем UID в /etc/passwd, если его там нет.
if ! whoami &>/dev/null; then
  echo "analyst:x:$(id -u):0:analyst:/home/spark:/bin/bash" >> /etc/passwd
fi
exec jupyter lab --ip=0.0.0.0 --port=8888 --no-browser \
  --ServerApp.token= --ServerApp.password= --ServerApp.root_dir=/opt/notebooks
