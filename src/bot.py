from rlbot.agents.base_agent import BaseAgent, SimpleControllerState
from rlbot.messages.flat.QuickChatSelection import QuickChatSelection
from rlbot.utils.structures.game_data_struct import GameTickPacket
import math
from util.ball_prediction_analysis import find_slice_at_time
from util.boost_pad_tracker import BoostPadTracker
from util.drive import steer_toward_target
from util.sequence import Sequence, ControlStep
from util.vec import Vec3


class TutorialBot(BaseAgent):
    def __init__(self, name, team, index):
        super().__init__(name, team, index)
        self.controller = SimpleControllerState()

        # Game values
        self.bot_pos = None
        self.bot_yaw = None
        self.state = "Thinking..."
        
    def aim(self, target_x, target_y):
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
            self.state = "Left..."

        elif angle_front_to_target > math.radians(10):
            # If the target is more than 10 degrees left from the centre, steer right
            self.controller.steer = 1
            self.state = "Right..."

        else:
            # If the target is less than 10 degrees from the centre, steer straight
            self.controller.steer = 0
            self.state = "On..."


    def get_output(self, packet: GameTickPacket) -> SimpleControllerState:
        # Update game data variables
        self.bot_yaw = packet.game_cars[self.team].physics.rotation.yaw
        self.bot_pos = packet.game_cars[self.index].physics.location

        ball_pos = packet.game_ball.physics.location
        if(self.index == 0):
            nemesis = packet.game_cars[1]
            nemesisColor = self.renderer.cyan()
        else:
            nemesis = packet.game_cars[0]
        my_car = packet.game_cars[self.index]
        car_location = Vec3(my_car.physics.location)
        car_velocity = Vec3(my_car.physics.velocity)
        ball_location = Vec3(packet.game_ball.physics.location)
        nemesis_location = Vec3(self.nemesis.physics.location)
        nemesis_velocity = Vec3(self.nemesis.physics.velocity)
        if(self.index == 0):
            # You can set more controls if you want, like controls.boost.
            self.renderer.draw_rect_2d(0, 0, 250, 250, True, self.renderer.cyan())
            self.renderer.draw_string_2d(5, 5, 2, 1, self.state, self.renderer.black())
            self.renderer.draw_string_2d(5, 60, 1, 1, f'{ball_location.x:.1f}' +", " + f'{ball_location.y:.1f}', self.renderer.black())
            self.renderer.draw_string_2d(5, 90, 1, 1, f'{car_location.dist(nemesis_location):.1f}' +", " + f'{car_location.dist(ball_location):.1f}', self.renderer.black())
            self.renderer.draw_string_2d(5, 120, 1, 1, str(car_location.dist(nemesis_location) < car_location.dist(ball_location)), self.renderer.black())
        else:
            self.renderer.draw_rect_2d(250, 0, 250, 250, True, self.renderer.orange())
            self.renderer.draw_string_2d(255, 5, 2, 1, self.state, self.renderer.black())
            self.renderer.draw_string_2d(255, 60, 1, 1, f'{ball_location.x:.1f}' +", " + f'{ball_location.y:.1f}', self.renderer.black())
            self.renderer.draw_string_2d(255, 90, 1, 1, f'{car_location.dist(nemesis_location):.1f}' +", " + f'{car_location.dist(ball_location):.1f}', self.renderer.black())
            self.renderer.draw_string_2d(255, 120, 1, 1, str(car_location.dist(nemesis_location) < car_location.dist(ball_location)), self.renderer.black())


        self.aim(ball_pos.x, ball_pos.y)

        self.controller.throttle = 1

        return self.controller