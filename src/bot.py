from rlbot.agents.base_agent import BaseAgent, SimpleControllerState
from rlbot.messages.flat.QuickChatSelection import QuickChatSelection
from rlbot.utils.structures.game_data_struct import GameTickPacket
import math
from util.ball_prediction_analysis import find_slice_at_time
from util.boost_pad_tracker import BoostPadTracker
from util.drive import steer_toward_target
from util.sequence import Sequence, ControlStep
from util.vec import Vec3


class MyBot(BaseAgent):

    def __init__(self, name, team, index):
        super().__init__(name, team, index)
        self.active_sequence: Sequence = None
        self.boost_pad_tracker = BoostPadTracker()
        if(self.index == 0):
            self.nemesis = GameTickPacket.game_cars[1]
        else:
            self.nemesis = GameTickPacket.game_cars[0]
        self.state

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
            self.controls.steer = -1
        elif angle_front_to_target > math.radians(10):
            # If the target is more than 10 degrees left from the centre, steer right
            self.controls.steer = 1
        else:
            # If the target is less than 10 degrees from the centre, steer straight
            self.controls.steer = 0
    def initialize_agent(self):
        # Set up information about the boost pads now that the game is active and the info is available
        self.boost_pad_tracker.initialize_boosts(self.get_field_info())
    def draw(self, packet:GameTickPacket):
        if(self.index == 0):
            self.nemesis = packet.game_cars[1]
            nemesisColor = self.renderer.cyan()
        else:
            self.nemesis = packet.game_cars[0]
            nemesisColor = self.renderer.orange()
        my_car = packet.game_cars[self.index]
        car_location = Vec3(my_car.physics.location)
        car_velocity = Vec3(my_car.physics.velocity)
        ball_location = Vec3(packet.game_ball.physics.location)
        nemesis_location = Vec3(self.nemesis.physics.location)
        nemesis_velocity = Vec3(self.nemesis.physics.velocity)
        if(self.index == 0):
            # You can set more controls if you want, like controls.boost.
            self.renderer.draw_rect_2d(0, 0, 250, 250, True, nemesisColor)
            self.renderer.draw_string_2d(5, 5, 2, 1, self.state, self.renderer.black())
            self.renderer.draw_string_2d(5, 60, 1, 1, f'{ball_location.x:.1f}' +", " + f'{ball_location.y:.1f}', self.renderer.black())
            self.renderer.draw_string_2d(5, 90, 1, 1, f'{car_location.dist(nemesis_location):.1f}' +", " + f'{car_location.dist(ball_location):.1f}', self.renderer.black())
            self.renderer.draw_string_2d(5, 120, 1, 1, str(car_location.dist(nemesis_location) < car_location.dist(ball_location)), self.renderer.black())
        else:
            self.renderer.draw_rect_2d(250, 0, 250, 250, True, nemesisColor)
            self.renderer.draw_string_2d(255, 5, 2, 1, self.state, self.renderer.black())
            self.renderer.draw_string_2d(255, 60, 1, 1, f'{ball_location.x:.1f}' +", " + f'{ball_location.y:.1f}', self.renderer.black())
            self.renderer.draw_string_2d(255, 90, 1, 1, f'{car_location.dist(nemesis_location):.1f}' +", " + f'{car_location.dist(ball_location):.1f}', self.renderer.black())
            self.renderer.draw_string_2d(255, 120, 1, 1, str(car_location.dist(nemesis_location) < car_location.dist(ball_location)), self.renderer.black())
 
    def get_output(self, packet: GameTickPacket) -> SimpleControllerState:
        """
        This function will be called by the framework many times per second. This is where you can
        see the motion of the ball, etc. and return controls to drive your car.
        """

        # Keep our boost pad info updated with which pads are currently active
        self.boost_pad_tracker.update_boost_status(packet)

        # This is good to keep at the beginning of get_output. It will allow you to continue
        # any sequences that you may have started during a previous call to get_output.
        if self.active_sequence and not self.active_sequence.done:
            controls = self.active_sequence.tick(packet)
            if controls is not None:
                return controls

        # Gather some information about our car and the ball
        my_car = packet.game_cars[self.index]
        car_location = Vec3(my_car.physics.location)
        car_velocity = Vec3(my_car.physics.velocity)
        ball_location = Vec3(packet.game_ball.physics.location)

        if(self.index == 0):
            nemesis = packet.game_cars[1]
            nemesisColor = self.renderer.cyan()
        else:
            nemesis = packet.game_cars[0]
            nemesisColor = self.renderer.orange()

        nemesis_location = Vec3(nemesis.physics.location)
        nemesis_velocity = Vec3(nemesis.physics.velocity)
        self.renderer.draw_line_3d(nemesis_location, car_location, self.renderer.red())
        self.controls = SimpleControllerState()

        if car_location.dist(nemesis_location) < car_location.dist(ball_location):
            target_location = nemesis_location
            self.renderer.draw_line_3d(nemesis_location, target_location, self.renderer.cyan())
            state = "Attacking"
            controls.boost = True
        elif car_location.dist(ball_location) > 1500:
            # We're far away from the ball, let's try to lead it a little bit
            ball_prediction = self.get_ball_prediction_struct()  # This can predict bounces, etc
            ball_in_future = find_slice_at_time(ball_prediction, packet.game_info.seconds_elapsed + 2)
            target_location = Vec3(ball_in_future.physics.location)
            self.renderer.draw_line_3d(ball_location, target_location, self.renderer.cyan())
            state = "Anticipating"
            # self.controller.boost = False
        else:
            target_location = ball_location
            state = "On Ball" 
            # self.controller.boost = True

        
        self.renderer.draw_line_3d(car_location, target_location, self.renderer.white())
        self.renderer.draw_string_3d(car_location, 1, 1, f'Speed: {car_velocity.length():.1f}', self.renderer.white())
        self.renderer.draw_string_3d(car_location, 3, 1, f'Ball: {ball_location.x:.1f}, {ball_location.y:.1f}', self.renderer.white())

        self.renderer.draw_rect_3d(target_location, 8, 8, True, self.renderer.cyan(), centered=True)

        if 750 < car_velocity.length() < 800:
            # We'll do a front flip if the car is moving at a certain speed.
            return self.begin_front_flip(packet)

        controls.steer = steer_toward_target(my_car, target_location)
        controls.throttle = 1.0
        if(self.index == 0):
            # You can set more controls if you want, like controls.boost.
            self.renderer.draw_rect_2d(0, 0, 250, 250, True, nemesisColor)
            self.renderer.draw_string_2d(5, 5, 2, 1, state, self.renderer.black())
            self.renderer.draw_string_2d(5, 60, 1, 1, f'{ball_location.x:.1f}' +", " + f'{ball_location.y:.1f}', self.renderer.black())
            self.renderer.draw_string_2d(5, 90, 1, 1, f'{car_location.dist(nemesis_location):.1f}' +", " + f'{car_location.dist(ball_location):.1f}', self.renderer.black())
            self.renderer.draw_string_2d(5, 120, 1, 1, str(car_location.dist(nemesis_location) < car_location.dist(ball_location)), self.renderer.black())
        else:
            self.renderer.draw_rect_2d(250, 0, 500, 250, True, nemesisColor)
            self.renderer.draw_string_2d(255, 5, 2, 1, state, self.renderer.black())
            self.renderer.draw_string_2d(255, 60, 1, 1, f'{ball_location.x:.1f}' +", " + f'{ball_location.y:.1f}', self.renderer.black())
            self.renderer.draw_string_2d(255, 90, 1, 1, f'{car_location.dist(nemesis_location):.1f}' +", " + f'{car_location.dist(ball_location):.1f}', self.renderer.black())
            self.renderer.draw_string_2d(255, 120, 1, 1, str(car_location.dist(nemesis_location) < car_location.dist(ball_location)), self.renderer.black())
 
        return controls

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
