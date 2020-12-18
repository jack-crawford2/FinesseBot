from rlbot.agents.base_agent import BaseAgent, SimpleControllerState
from rlbot.messages.flat.QuickChatSelection import QuickChatSelection
from rlbot.utils.structures.game_data_struct import GameTickPacket
import math
from util.ball_prediction_analysis import find_slice_at_time
from util.boost_pad_tracker import BoostPadTracker
from util.drive import steer_toward_target
from util.sequence import Sequence, ControlStep
from util.vec import Vec3


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

        if angle_front_to_target < math.radians(-10):
            # If the target is more than 10 degrees right from the centre, steer left
            self.controller.steer = -1
        elif angle_front_to_target > math.radians(10):
            # If the target is more than 10 degrees left from the centre, steer right
            self.controller.steer = 1
        else:
            # If the target is less than 10 degrees from the centre, steer straight
            self.controller.steer = 0

    def aim_between_defense(self, ball_x, ball_y, goaly):
        angle_between_bot_and_ball = math.atan2(ball_y - self.bot_pos.y, ball_x - self.bot_pos.x)
        angle_front_to_ball = angle_between_bot_and_ball - self.bot_yaw

        angle_between_bot_and_goal = math.atan2(goaly - self.bot_pos.y, 0 - self.bot_pos.x)
        angle_front_to_goal = angle_between_bot_and_goal - self.bot_yaw

        # Correct the values
        if angle_front_to_ball < -math.pi:
            angle_front_to_ball += 2 * math.pi
        if angle_front_to_ball > math.pi:
            angle_front_to_ball -= 2 * math.pi

        if angle_front_to_goal < -math.pi:
                angle_front_to_goal += 2 * math.pi
        if angle_front_to_goal > math.pi:
            angle_front_to_goal -= 2 * math.pi

        if (angle_between_bot_and_goal - angle_between_bot_and_ball) < math.radians(-30):
            self.state = "left"
            self.controller.steer = -1
        elif (angle_between_bot_and_goal - angle_between_bot_and_ball) > math.radians(30):
            self.controller.steer = 1
            self.state = "right"
        # elif angle_front_to_ball < math.radians(-10):
        #     # If the target is more than 10 degrees right from the centre, steer left
        #     self.controller.steer = -1
        # elif angle_front_to_ball > math.radians(10):
        #     # If the target is more than 10 degrees left from the centre, steer right
        #     self.controller.steer = 1
        else:
            # If the target is less than 10 degrees from the centre, steer straight
            self.controller.steer = 0
    
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
        else:
            nemesis = packet.game_cars[0]
            goaly = -5000
        my_car = packet.game_cars[self.index]
        car_location = Vec3(my_car.physics.location)
        car_velocity = Vec3(my_car.physics.velocity)
        ball_location = Vec3(packet.game_ball.physics.location)
        nemesis_location = Vec3(nemesis.physics.location)
        nemesis_velocity = Vec3(nemesis.physics.velocity)
       
        # self.aim(ball_pos.x, ball_pos.y, goaly)
        self.state = "trying defense"

        if car_location.dist(nemesis_location) < 20:
            self.state = "flipStuck?"
            return self.begin_front_flip(packet)
        elif ball_location.x == 0 and ball_location.y == 0:
            self.aim(0, 0, goaly)
        else:
            self.aim_between_defense(ball_location.x, ball_location.y, goaly)

        # if 200 < car_velocity.length() < 800:
        #     self.state = "flipSpeed?"
        #     # We'll do a front flip if the car is moving at a certain speed.
        #     self.controller.boost = True
        # if car_location.dist(ball_location) > 350:
        #     self.state = "Boost?"
        #     self.controller.boost = True
        # if(self.index == 0):
        #     if ball_location.y > (goaly-500) and car_location.y > (goaly-750):
        #         #aim for goal
        #         self.aim(ball_location.x, ball_location.y, goaly)
        #         self.state = "Shot?"
        #     elif(ball_location.y+500 > car_location.y):
        #         self.aim(ball_location.x, ball_location.y, goaly)
        #         self.state = "Offense"
        #     else: 
        #         self.aim(0, -goaly, goaly)
        #         self.state = "Defense"
        # else:
        #     if ball_location.y < (goaly+500) and car_location.y < (goaly+750):
        #         #aim for goal
        #         self.aim(ball_location.x, ball_location.y, goaly)
        #         self.state = "Shot?"
        #     elif(ball_location.y-500 < car_location.y):
        #         self.state = "Offense"
        #         self.aim(ball_location.x, ball_location.y, goaly)
        #     else: 
        #         self.aim(0, -goaly, goaly)
        #         self.state = "Defense"
        angle_between_bot_and_ball = math.atan2(ball_location.y - self.bot_pos.y, ball_location.x - self.bot_pos.x)
        angle_front_to_ball = angle_between_bot_and_ball - self.bot_yaw
        
        angle_between_bot_and_goal = math.atan2(goaly - self.bot_pos.y, 0 - self.bot_pos.x)
        angle_front_to_goal = angle_between_bot_and_goal - self.bot_yaw
        if angle_front_to_ball < -math.pi:
            angle_front_to_ball += 2 * math.pi
        if angle_front_to_ball > math.pi:
            angle_front_to_ball -= 2 * math.pi

        if angle_front_to_goal < -math.pi:
                angle_front_to_goal += 2 * math.pi
        if angle_front_to_goal > math.pi:
            angle_front_to_goal -= 2 * math.pi
        if(self.index == 0):
            # You can set more controls if you want, like controls.boost.
            self.renderer.draw_rect_2d(0, 0, 250, 250, True, self.renderer.cyan())
            self.renderer.draw_string_2d(5, 5, 2, 1, self.state, self.renderer.black())
            self.renderer.draw_string_2d(5, 60, 1, 1, f'{ball_location.x:.1f}' +", " + f'{ball_location.y:.1f}', self.renderer.black())
            self.renderer.draw_string_2d(5, 90, 1, 1, f'{car_location.dist(nemesis_location):.1f}' +", " + f'{car_location.dist(ball_location):.1f}', self.renderer.black())
            self.renderer.draw_string_2d(5, 120, 1, 1, str(car_location.dist(nemesis_location) < car_location.dist(ball_location)), self.renderer.black())
            self.renderer.draw_string_2d(5, 150, 1, 1, str(angle_between_bot_and_goal - angle_between_bot_and_ball), self.renderer.black())
            self.renderer.draw_string_2d(5, 180, 1, 1, str(self.bot_yaw), self.renderer.black())

        else:
            self.renderer.draw_rect_2d(250, 0, 250, 250, True, self.renderer.orange())
            self.renderer.draw_string_2d(255, 5, 2, 1, self.state, self.renderer.black())
            self.renderer.draw_string_2d(255, 60, 1, 1, str(self.bot_yaw), self.renderer.black())
            self.renderer.draw_string_2d(255, 90, 1, 1, f'{car_location.dist(nemesis_location):.1f}' +", " + f'{car_location.dist(ball_location):.1f}', self.renderer.black())
            self.renderer.draw_string_2d(255, 120, 1, 1, str(car_location.dist(nemesis_location) < car_location.dist(ball_location)), self.renderer.black())
            self.renderer.draw_string_2d(255, 150, 1, 1, str(angle_between_bot_and_goal - angle_between_bot_and_ball), self.renderer.black())
            self.renderer.draw_string_2d(255, 180, 1, 1, str(self.bot_yaw), self.renderer.black())

        self.controller.throttle = 1

        return self.controller