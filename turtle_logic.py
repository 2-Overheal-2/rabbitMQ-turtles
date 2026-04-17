#!/usr/bin/env python
# -*- coding: utf-8 -*-
import math

class TurtleFollowerLogic:
    def __init__(self, max_speed=1.0, stop_distance=0.6):
        self.max_speed = max_speed
        self.stop_distance = stop_distance
        self.k_linear = 1.2
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