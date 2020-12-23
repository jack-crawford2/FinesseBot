from rlbot.agents.base_agent import BaseAgent, SimpleControllerState
from rlbot.messages.flat.QuickChatSelection import QuickChatSelection
from rlbot.utils.structures.game_data_struct import GameTickPacket
import math
from util.ball_prediction_analysis import find_slice_at_time
from util.boost_pad_tracker import BoostPadTracker
from util.drive import steer_toward_target
from util.sequence import Sequence, ControlStep
from util.vec import Vec3
import random

class FinesseBot(BaseAgent):
    def __init__(self, name, team, index):
        super().__init__(name, team, index)
        self.controller = SimpleControllerState()
        self.active_sequence: Sequence = None

        # Game values
        self.bot_pos = None
        self.bot_yaw = None
        self.state = "Thinking..."
        
    def aim(self, target_x, target_y, goaly):
        angle_between_bot_and_target = math.atan2(target_y - self.bot_pos.y, target_x - self.bot_pos.x)

        angle_front_to_target = angle_between_bot_and_target - self.bot_yaw

        # Correct the values
        if angle_front_to_target < -math.pi:
            angle_front_to_target += 2 * math.pi
        if angle_front_to_target > math.pi:
            angle_front_to_target -= 2 * math.pi
        if angle_front_to_target > math.radians(32) or angle_front_to_target < math.radians(-32):
            self.controller.handbrake = True
            self.controller.steer = -1
            self.controller.yaw = 1
        else:
            self.controller.handbrake = False
            
        if angle_front_to_target < math.radians(-10):
            # If the target is more than 10 degrees right from the centre, steer left
            self.controller.steer = -1
        elif angle_front_to_target > math.radians(10):
            # If the target is more than 10 degrees left from the centre, steer right
            self.controller.steer = 1
        else:
            # If the target is less than 10 degrees from the centre, steer straight
            self.controller.steer = 0
    
    def clamp(self, direction, start, end):
        is_right = direction.dot(end.cross(Vec3(0,0,-1))) < 0
        is_left = direction.dot(start.cross(Vec3(0,0,-1))) < 0

        if end.dot(start.cross(Vec3(0,0,-1))) > 0 if (is_right and is_left) else is_right or is_left:
            return direction

        if (start.dot(direction) < end.dot(direction)):
            return end

        return start

    def shoot(self, ball_location, goaly):
        car_to_ball = Vec3(ball_location - self.bot_pos)
        car_to_ball_direction = Vec3(car_to_ball.normalized())

        ball_to_left_target_direction = Vec3(Vec3(-890, goaly, 0) - ball_location).normalized()
        ball_to_right_target_direction = Vec3(Vec3(890, goaly, 0) - ball_location).normalized()
        
        direction_of_approach = Vec3(self.clamp(car_to_ball_direction, ball_to_left_target_direction, ball_to_right_target_direction))
        offset_ball_location = Vec3(ball_location - (direction_of_approach * 92.75))
        self.aim(offset_ball_location.x, offset_ball_location.y, goaly)

    def begin_front_flip(self, packet):
            # Send some quickchat just for fun
        self.send_quick_chat(team_only=False, quick_chat=QuickChatSelection.Information_IGotIt)

        # Do a front flip. We will be committed to this for a few seconds and the bot will ignore other
        # logic during that time because we are setting the active_sequence.
        self.active_sequence = Sequence([
            ControlStep(duration=0.05, controls=SimpleControllerState(jump=True)),
            ControlStep(duration=0.05, controls=SimpleControllerState(jump=False)),
            ControlStep(duration=0.2, controls=SimpleControllerState(jump=True, pitch=-1)),
            ControlStep(duration=0.8, controls=SimpleControllerState()),
        ])

        # Return the controls associated with the beginning of the sequence so we can start right away.
        return self.active_sequence.tick(packet)

    def get_output(self, packet: GameTickPacket) -> SimpleControllerState:
        # Update game data variables
        self.bot_yaw = packet.game_cars[self.team].physics.rotation.yaw
        self.bot_pos = packet.game_cars[self.index].physics.location

        ball_pos = packet.game_ball.physics.location
        if(self.index == 0):
            nemesis = packet.game_cars[1]
            goaly = 5000
            mygoal = -1
        else:
            nemesis = packet.game_cars[0]
            goaly = -5000
            mygoal = 1

        my_car = packet.game_cars[self.index]
        car_location = Vec3(my_car.physics.location)
        car_velocity = Vec3(my_car.physics.velocity)
        ball_location = Vec3(packet.game_ball.physics.location)
        nemesis_location = Vec3(nemesis.physics.location)
        nemesis_velocity = Vec3(nemesis.physics.velocity)
       
        # self.aim(ball_pos.x, ball_pos.y, goaly)
        # self.state = "trying defense"

        ball_to_home_y = abs(-goaly - ball_location.y)
        car_to_home_y = abs(-goaly - car_location.y)
        car_to_ball = car_location.dist(ball_location)
        car_to_nem = car_location.dist(nemesis_location)
        if ball_location.x == 0 and ball_location.y == 0:
            self.state = "kickoff"
            self.controller.boost = True
            self.aim(ball_location.x, ball_location.y, goaly)
        elif random.randint(1, 100000) == 69:
            self.state = "fuckit"
            self.controller.handbrake = True
            self.controller.steer = -1
            self.controller.yaw = 1
        elif car_location.dist(nemesis_location) < 175:
            self.state = "avoid"
            self.controller.jump = True
            self.controller.roll = -1
            self.controller.throttle = 0.7
            self.controller.steer = -1
            return self.controller
        elif ball_to_home_y < car_to_home_y:
            self.state = "d pos"
            self.aim((ball_location.x)/2, mygoal*abs(goaly - ball_location.y)/2, goaly)
        else:
            # self.aim(ball_location.x, ball_location.y, goaly)
            self.shoot(ball_location, goaly)
            self.state = "attack"
            if car_location.dist(ball_location) > 500 or (ball_location.x == 0 and ball_location.y == 0):
                self.controller.boost = True
            if car_location.dist(ball_location) < 150:
                self.controller.pitch = -1
                self.controller.jump = True
        if(self.index == 0):
            self.renderer.draw_rect_2d(0, 0, 250, 250, True, self.renderer.cyan())
            self.renderer.draw_string_2d(5, 5, 2, 1, self.state, self.renderer.black())
            self.renderer.draw_string_2d(5, 60, 1, 1, "b2h: " + f'{ball_to_home_y:.1f}', self.renderer.black())
            self.renderer.draw_string_2d(5, 90, 1, 1, "c2h: " + f'{car_to_home_y:.1f}', self.renderer.black())
            self.renderer.draw_string_2d(5, 120, 1, 1, "c2b: " + f'{car_to_ball:.1f}', self.renderer.black())
            self.renderer.draw_string_2d(5, 150, 1, 1, "c2n: " + f'{car_to_nem:.1f}', self.renderer.black())
            # self.renderer.draw_string_2d(5, 180, 1, 1, "v: " + str(my_car.physics.velocity), self.renderer.black())

        else:
            self.renderer.draw_rect_2d(250, 0, 250, 250, True, self.renderer.orange())
            self.renderer.draw_string_2d(255, 5, 2, 1, self.state, self.renderer.black())
            self.renderer.draw_string_2d(255, 60, 1, 1, "b2h: " + f'{ball_to_home_y:.1f}', self.renderer.black())
            self.renderer.draw_string_2d(255, 90, 1, 1, "c2h: " + f'{car_to_home_y:.1f}', self.renderer.black())
            self.renderer.draw_string_2d(255, 120, 1, 1, "c2b: " + f'{car_to_ball:.1f}', self.renderer.black())
            self.renderer.draw_string_2d(255, 150, 1, 1, "c2n: " + f'{car_to_nem:.1f}', self.renderer.black())
            # self.renderer.draw_string_2d(255, 180, 1, 1, "v: " +str(my_car.physics.velocity), self.renderer.black())


        self.controller.throttle = 1

        return self.controller