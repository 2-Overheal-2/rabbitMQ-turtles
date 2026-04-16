import json
import math
import threading
import time
from collections import deque

import pika
import pygame


RABBITMQ_HOST = "localhost"
QUEUE_NAME = "turtle_commands"

WINDOW_WIDTH = 900
WINDOW_HEIGHT = 700
BACKGROUND_COLOR = (240, 240, 240)
LEADER_COLOR = (0, 120, 255)
FOLLOWER_COLOR = (0, 180, 100)
TEXT_COLOR = (20, 20, 20)
BORDER_COLOR = (0, 0, 0)

TURTLE_SIZE = 22
MAX_HISTORY = 5000

WORLD_MIN = 0.0
WORLD_MAX_X = 11.0
WORLD_MAX_Y = 11.0


class TurtleFollowerLogic:
    def __init__(self, max_speed=2.5, stop_distance=0.35):
        self.max_speed = max_speed
        self.stop_distance = stop_distance
        self.k_linear = 2.0
        self.k_angular = 4.5

    def compute_cmd(self, curr_x, curr_y, curr_theta, tgt_x, tgt_y):
        dx = tgt_x - curr_x
        dy = tgt_y - curr_y
        dist = math.hypot(dx, dy)

        if dist < self.stop_distance:
            return 0.0, 0.0

        angle_to_target = math.atan2(dy, dx)
        angle_error = angle_to_target - curr_theta

        while angle_error > math.pi:
            angle_error -= 2.0 * math.pi
        while angle_error < -math.pi:
            angle_error += 2.0 * math.pi

        linear = min(self.max_speed, self.k_linear * dist)
        angular = self.k_angular * angle_error

        return linear, angular


class Turtle:
    def __init__(self, x, y, color, is_leader=False, start_delay=0.0):
        self.x = x
        self.y = y
        self.color = color
        self.is_leader = is_leader
        self.angle = 0.0
        self.linear_velocity = 0.0
        self.angular_velocity = 0.0
        self.start_delay = max(0.0, start_delay)
        self.spawn_time = time.time()
        self.logic = None if is_leader else TurtleFollowerLogic()

    def active(self):
        return (time.time() - self.spawn_time) >= self.start_delay


velocity_queue = deque()
queue_lock = threading.Lock()


def get_turtle_count():
    while True:
        try:
            value = input("Введите количество черепашек: ").strip()
            count = int(value)
            if count < 2:
                print("Количество должно быть не меньше 2.")
                continue
            return count
        except ValueError:
            print("Нужно ввести целое число.")


def rabbitmq_consumer():
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host=RABBITMQ_HOST)
    )
    channel = connection.channel()
    channel.queue_declare(queue=QUEUE_NAME)

    def callback(ch, method, properties, body):
        try:
            data = json.loads(body.decode())
            linear = float(data.get("linear", 0.0))
            angular = float(data.get("angular", 0.0))
            with queue_lock:
                velocity_queue.append((linear, angular))
        except Exception as e:
            print("Ошибка чтения сообщения:", e)

    channel.basic_consume(
        queue=QUEUE_NAME,
        on_message_callback=callback,
        auto_ack=True
    )

    print("Ожидание сообщений из RabbitMQ...")
    channel.start_consuming()


def clamp(value, min_value, max_value):
    return max(min_value, min(value, max_value))


def world_to_screen(x, y):
    screen_x = int((x / WORLD_MAX_X) * WINDOW_WIDTH)
    screen_y = int(WINDOW_HEIGHT - (y / WORLD_MAX_Y) * WINDOW_HEIGHT)
    return screen_x, screen_y


def update_turtle_pose(turtle, dt):
    turtle.angle += turtle.angular_velocity * dt

    while turtle.angle > math.pi:
        turtle.angle -= 2.0 * math.pi
    while turtle.angle < -math.pi:
        turtle.angle += 2.0 * math.pi

    turtle.x += turtle.linear_velocity * math.cos(turtle.angle) * dt
    turtle.y += turtle.linear_velocity * math.sin(turtle.angle) * dt

    turtle.x = clamp(turtle.x, WORLD_MIN, WORLD_MAX_X)
    turtle.y = clamp(turtle.y, WORLD_MIN, WORLD_MAX_Y)


def update_followers(turtles, dt):
    for i in range(1, len(turtles)):
        follower = turtles[i]

        if not follower.active():
            follower.linear_velocity = 0.0
            follower.angular_velocity = 0.0
            continue

        target = turtles[i - 1]

        linear, angular = follower.logic.compute_cmd(
            curr_x=follower.x,
            curr_y=follower.y,
            curr_theta=follower.angle,
            tgt_x=target.x,
            tgt_y=target.y
        )

        follower.linear_velocity = linear
        follower.angular_velocity = angular

        update_turtle_pose(follower, dt)


def draw_turtle(screen, turtle, index):
    x, y = world_to_screen(turtle.x, turtle.y)
    angle = -turtle.angle
    size = TURTLE_SIZE

    p1 = (x + math.cos(angle) * size, y + math.sin(angle) * size)
    p2 = (x + math.cos(angle + 2.5) * size * 0.7, y + math.sin(angle + 2.5) * size * 0.7)
    p3 = (x + math.cos(angle - 2.5) * size * 0.7, y + math.sin(angle - 2.5) * size * 0.7)

    pygame.draw.polygon(
        screen,
        turtle.color,
        [(int(p1[0]), int(p1[1])),
         (int(p2[0]), int(p2[1])),
         (int(p3[0]), int(p3[1]))]
    )

    font = pygame.font.SysFont(None, 20)
    label = font.render(str(index), True, (255, 255, 255))
    screen.blit(label, (x - 5, y - 7))


def create_turtles(count):
    turtles = []

    leader = Turtle(
        x=5.5,
        y=5.5,
        color=LEADER_COLOR,
        is_leader=True
    )
    turtles.append(leader)

    for i in range(2, count + 1):
        if i % 2 == 0:
            spawn_x, spawn_y = 1.0, 1.0
        else:
            spawn_x, spawn_y = 9.0, 9.0

        delay_seconds = (i - 2) * 1.5

        turtle = Turtle(
            x=spawn_x,
            y=spawn_y,
            color=FOLLOWER_COLOR,
            is_leader=False,
            start_delay=delay_seconds
        )

        turtles.append(turtle)

    return turtles


def draw_path(screen, path_points):
    if len(path_points) < 2:
        return

    points = [world_to_screen(x, y) for x, y in path_points]
    pygame.draw.lines(screen, (180, 180, 180), False, points, 2)


def main():
    turtle_count = get_turtle_count()

    consumer_thread = threading.Thread(target=rabbitmq_consumer, daemon=True)
    consumer_thread.start()

    pygame.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("RabbitMQ Turtle Simulator")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 28)

    turtles = create_turtles(turtle_count)

    leader_history = deque(maxlen=MAX_HISTORY)
    leader_history.append((turtles[0].x, turtles[0].y))

    running = True
    frame_counter = 0
    start_time = time.time()

    while running:
        dt = clock.tick(60) / 1000.0
        frame_counter += 1

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False

        with queue_lock:
            while velocity_queue:
                linear, angular = velocity_queue.popleft()
                turtles[0].linear_velocity = linear
                turtles[0].angular_velocity = angular

        update_turtle_pose(turtles[0], dt)
        leader_history.append((turtles[0].x, turtles[0].y))

        update_followers(turtles, dt)

        screen.fill(BACKGROUND_COLOR)
        pygame.draw.rect(screen, BORDER_COLOR, (0, 0, WINDOW_WIDTH, WINDOW_HEIGHT), 3)

        draw_path(screen, leader_history)

        for i, turtle in enumerate(turtles):
            draw_turtle(screen, turtle, i)

        info_lines = [
            f"Черепашек: {len(turtles)}",
            "Управление в controller.py, ESC - выход"
        ]

        y = 20
        for line in info_lines:
            text = font.render(line, True, TEXT_COLOR)
            screen.blit(text, (20, y))
            y += 28

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()