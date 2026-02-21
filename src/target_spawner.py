#! usr/bin/env python3
import rclpy
from rclpy.node import Node
from turtlesim.srv import Spawn
import random
from functools import partial
from tutorial_interfaces.msg import TurtleData, TurtleArray
from tutorial_interfaces.srv import KillTurtle
from turtlesim.srv import Kill

class TurtleSpawner(Node):       #main class
    def __init__(self):
        super().__init__("turtle_spawner")         #node name
        self.spawn_turtle = self.create_client(Spawn, "/spawn")       #create client to spawn the turtles
        self.turtles_publisher = self.create_publisher(TurtleArray, "turtles_data", 10)       #publist the turtles list
        self.kill_turtle_service = self.create_service(KillTurtle, 'kill_turtle', self.kill_turtle_callback)     #service for the rerquest from the controller
        self.kill_turtle_client = self.create_client(Kill, '/kill')     #client to call the turtle kill service in turtlesim
        self.name_counter = 1        #name counter to give unique names to the spawned turtles, this is incremented every time a new turtle is spawned
        self.turtles_list_ = []      #list of turtles data to store the data of all the spawned turtles, this is published to the controller node to get the target coordinates of the newly spawned turtles
        self.call_timer = self.create_timer(1.5, self.call_spawn_service)   #timer to call the spawn service

    def kill_turtle_callback(self, request: KillTurtle.Request, response: KillTurtle.Response):   #response to the controller'request and send it further to the kill service
        self.call_kill_turtle_client(request.name)      #call the kill service with turtle name
        response.success = True
        return response

    def call_kill_turtle_client(self, turtle_name):      #function to call service to kill turtle
        self.get_logger().info(f"Received request to kill turtle: {turtle_name}")

        while not self.kill_turtle_client.wait_for_service(timeout_sec=1.0):
            self.get_logger().warn("Kill service not available, waiting...")

        kill_request = Kill.Request() #create a request for the kill service, this is the service provided by turtlesim to kill a turtle, we need to call this service to remove the target turtle from the simulation once it is reached
        kill_request.name = turtle_name #set the name

        future = self.kill_turtle_client.call_async(kill_request)
        future.add_done_callback(partial(self.handle_kill_response, turtle_name=turtle_name))

    def handle_kill_response(self, future, turtle_name):      #callback function to handle the response from the kill service, this is called when the kill service responds to the kill request, it removes the killed turtle from the turtles list and publishes the updated list to the controller
        response = future.result()
        self.get_logger().info(f"Kill response for turtle {turtle_name}: {response}")  
        for i, turtle in enumerate(self.turtles_list_):  #iterate through the turtles list to find the turtle with the name that matches the killed turtle, and remove it from the list
            if turtle.name == turtle_name:
                self.turtles_list_.pop(i)
                self.publish_turtles_data()
                break

    def call_spawn_service(self):       #function to send requst to spawn service, this is called by the timer every 2 seconds to spawn a new turtle at random coordinates with a random orientation, and a unique name
        self.name_counter += 1
        x = random.uniform(0.5, 10.5)  #generate random x and y coordinates for the new turtle, the turtlesim environment is 11x11 units, so we generate coordinates between 0.5 and 10.5 to avoid spawning turtles too close to the walls
        y = random.uniform(0.5, 10.5)
        theta = random.uniform(0.0, 6.28)
        name =  "turtle" + str(self.name_counter)  #generate a unique name for the new turtle using the name counter, this ensures that each turtle has a unique name like turtle2, turtle3, etc.
        self.send_spawn_request(x, y, theta, name)    #call the function to send the request to the spawn service with the generated coordinates, orientation and name

    def send_spawn_request(self, x, y, theta, name): #function to send the request to the spawn service, this is called by the call_spawn_service function with the generated coordinates, orientation and name for the new turtle
        while not self.spawn_turtle.wait_for_service(timeout_sec=1.0):
            self.get_logger().warn("Service not available, waiting...")

        request = Spawn.Request() #create a request for the spawn service, this is the service provided by turtlesim to spawn a turtle, we need to call this service to add a new turtle to the simulation
        request.x = x
        request.y = y
        request.theta = theta
        request.name = name

        future = self.spawn_turtle.call_async(request) #call the spawn service asynchronously with the request, this allows the node to continue executing while waiting for the response from the service, and the response is handled in the callback function handle_response
        future.add_done_callback(partial(self.handle_response, request=request))

    def handle_response(self, future, request): #callback function to handle the response from the spawn service, this is called when the spawn service responds to the spawn request, it adds the new turtle's data to the turtles list and publishes the updated list to the controller
        response = future.result()
        data = TurtleData() #create a TurtleData message to store the data of the newly spawned turtle, this is the message type defined in the tutorial_interfaces package, it has fields for name, x, y and theta
        
        if response.name != "": #check if name exists
            self.get_logger().info(f"Successfully spawned turtle: {response.name}")
            data.name = response.name
            data.x = request.x
            data.y = request.y
            data.theta = request.theta
            self.turtles_list_.append(data) #add the new turtle's data to the turtles list, this list is published to the controller node to get the target coordinates of the newly spawned turtles
            self.publish_turtles_data() #publish the updated turtles list to the controller, this is to get the target coordinates of the newly spawned turtle, and update the controller's target accordingly, this is done every time a new turtle is spawned or a turtle is killed

    def publish_turtles_data(self): #function to publish the turtles list to the controller, this is called every time a new turtle is spawned or a turtle is killed to update the controller with the latest data of all the turtles in the simulation
        msg = TurtleArray() #create a TurtleArray message to store the list of turtles data, this is the message type defined in the tutorial_interfaces package, it has a field for a list of TurtleData messages
        msg.turtles = self.turtles_list_
        self.turtles_publisher.publish(msg) #publish the turtles list to the turtles_data topic, this is to get the target coordinates of the newly spawned turtles, and update the controller's target accordingly, this is done every time a new turtle is spawned or a turtle is killed

def main(args=None): #main function to initialize the node and spin it
    rclpy.init(args=args)
    node = TurtleSpawner()
    rclpy.spin(node)
    node.destroy_node()#destroy the node
    rclpy.shutdown() #shutdown the node

if __name__ == "__main__":
    main()
