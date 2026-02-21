#! /usr/bin/env python3

import rclpy
import math
from rclpy.node import Node
from turtlesim.msg import Pose
from geometry_msgs.msg import Twist
from tutorial_interfaces.msg import TurtleArray
from tutorial_interfaces.msg import TurtleData
from tutorial_interfaces.srv import KillTurtle
from functools import partial

class TargetChaser(Node):
    def __init__(self):
        super().__init__('controller')

        self.pose_ = None            #keep the initial target to none, the target will be set to the desired coordinates in the controller loop
        self.target = None

        # Create publisher
        self.cmd_vel_publisher_ = self.create_publisher(             #create a publisher to send velocity commands to the turtle
            Twist,
            'turtle1/cmd_vel',
            10  # QoS depth
        )

        self.pose_listener = self.create_subscription(               #create a subscription to listen to the turtle's current pose, which is published on the /turtle1/pose topic
            Pose,    
            'turtle1/pose',
            self.pose_callback,
            10
        )

        self.turtles_data_listener = self.create_subscription(
            TurtleArray,
            'turtles_data',
            self.turtles_data_callback,
            10
        )              #create a subscription to listen to the data of all turtles, which is published on the turtles_data topic by the spawner node, this is to get the target coordinates of the newly spawned turtles

        self.kill_turtle_client = self.create_client(KillTurtle, 'kill_turtle')

        self.timer = self.create_timer(0.05, self.controller_loop)   #create a timer to call the controller loop at a regular interval (20 Hz in this case, which means the loop will be called every 0.05 seconds)

    def pose_callback(self, msg):             #callback function to update the turtle's current pose whenever a new message is received on the /turtle1/pose topic, the pose is stored in the self.pose_ variable for use in the controller loop
        self.pose_ = msg

    def turtles_data_callback(self, msg : TurtleArray):     #callback function to update the target coordinates whenever a new message is received on the turtles_data topic, this is to get the target coordinates of the newly spawned turtles
        if len(msg.turtles) > 0:
            self.target = msg.turtles[0]         #get the last turtle in the list, which is the most recently spawned turtle, and set its coordinates as the target for the chaser turtle
            
    def controller_loop(self):         #main controller loop to calculate the velocity commands based on the current pose and the target coordinates, and publish the commands to move the turtle towards the target

        if self.pose_ == None or self.target == None:         #if pose is none then dont do anything, this is to prevent errors when the node starts and the pose has not been received yet
            return
        
        cmd = Twist()
        dx = self.target.x - self.pose_.x      #calculate x and y distance individually
        dy = self.target.y - self.pose_.y

        distance = math.sqrt(dx * dx + dy * dy)   #direct distance using pythagorus theorem, this is the distance from the turtle to the target
        d_theta = math.atan2(dy, dx)              #desired angle to the target, calculated using atan2 which gives the angle between the positive x-axis and the point (dx, dy)
        target_angle = d_theta - self.pose_.theta    #angle difference between the desired angle and the turtle's current orientation, this is the angle that the turtle needs to turn to face the target

        if distance > 0.3:         #tolerance to prevent oscillation when the turtle is close to the target
            target_angle = math.atan2(math.sin(target_angle), math.cos(target_angle)) #normalize the angle between -pi to pi
            self.target_reached = False
            cmd.linear.x = 2 * distance          #multiplier works as proportional constant, larger the distance, faster the turtle moves
            cmd.angular.z = 6 * target_angle     #larger the angle, faster and smaller the turn

        else:                      #if the turtle is close enough to the target, stop moving
            cmd.linear.x = 0.0
            cmd.angular.z = 0.0
            self.call_kill_turtle_service(self.target.name)     #call the kill turtle service to remove the target turtle from the simulation once it is reached
            self.target = None
            
        self.cmd_vel_publisher_.publish(cmd)       #publish the command to /turtle1/cmd_vel topic

    def call_kill_turtle_service(self, turtle_name):    #function to call the kill turtle service, this is called when the target is reached to remove the target turtle from the simulation
        while not self.kill_turtle_client.wait_for_service(timeout_sec=1.0):
            self.get_logger().warn("KillTurtle service not available, waiting...")

        request = KillTurtle.Request()
        request.name = turtle_name

        future = self.kill_turtle_client.call_async(request)
        future.add_done_callback(partial(self.handle_kill_response, turtle_name=turtle_name))

    def handle_kill_response(self, future, turtle_name):
        response = future.result()
        self.get_logger().info(f"Kill response for turtle {turtle_name}: {response}")

def main(args=None):             #main function to initialize the node and spin it
    rclpy.init(args=args)
    node = TargetChaser()      
    rclpy.spin(node)
    node.destroy_node()         #destrying the node is a good practise to free up resources when the node is no longer needed
    rclpy.shutdown()            #shutdown the ROS client library to clean up any resources used by the node

if __name__ == '__main__':      #call the main function when the script is executed directly
    main()
