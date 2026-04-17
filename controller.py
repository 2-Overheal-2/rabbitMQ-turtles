import json
import time
import pika
import pygame


RABBITMQ_HOST = "localhost"
QUEUE_NAME = "turtle_commands"

LINEAR_STEP = 1.0
ANGULAR_STEP = 1.0


def create_channel():
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host=RABBITMQ_HOST)
    )
    channel = connection.channel()
    channel.queue_declare(queue=QUEUE_NAME)
    return connection, channel


def send_velocity(channel, linear, angular):
    message = {
        "linear": linear,
        "angular": angular,
        "timestamp": time.time(),
    }
    channel.basic_publish(
        exchange="",
        routing_key=QUEUE_NAME,
        body=json.dumps(message)
    )


def main():
    connection, channel = create_channel()

    pygame.init()
    screen = pygame.display.set_mode((650, 240))
    pygame.display.set_caption("Turtle Controller")
    font = pygame.font.SysFont(None, 28)
    clock = pygame.time.Clock()

    running = True

    while running:
        screen.fill((30, 30, 30))

        lines = [
            "UP    -> вперед",
            "DOWN  -> назад",
            "LEFT  -> поворот влево",
            "RIGHT -> поворот вправо",
            "SPACE -> стоп",
            "ESC   -> выход"
        ]

        y = 20
        for line in lines:
            text = font.render(line, True, (255, 255, 255))
            screen.blit(text, (20, y))
            y += 30

        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_UP:
                    send_velocity(channel, LINEAR_STEP, 0.0)
                elif event.key == pygame.K_DOWN:
                    send_velocity(channel, -LINEAR_STEP, 0.0)
                elif event.key == pygame.K_LEFT:
                    send_velocity(channel, 0.0, ANGULAR_STEP)
                elif event.key == pygame.K_RIGHT:
                    send_velocity(channel, 0.0, -ANGULAR_STEP)
                elif event.key == pygame.K_SPACE:
                    send_velocity(channel, 0.0, 0.0)

        clock.tick(60)

    connection.close()
    pygame.quit()


if __name__ == "__main__":
    main()