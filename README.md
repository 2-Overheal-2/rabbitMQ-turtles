# rabbitMQ-turtles

## Скачиваем нужные зависимости

`pip install -r requirments.txt`

## Открываем первый терминал запускаем docker-compose

```
docker build .
docker compose -d 
```
## Открываем второй терминал запускаем simulator.py

`python3 simulator.py`

## Открываем третий терминал и запускаем controller.py

`python3 controller.py`

## Использование
При запуске simulator.py спрашивает сколько мы хотим черепашек (меньше 2 нельзя), после чего запускается программа. Управляем стрелочками как в ROSе, тормозим на пробел, радуемся жизни. 
