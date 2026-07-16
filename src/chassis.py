# src/chassis.py
import csv
import time
import os
from datetime import datetime

class ChassisController:
    def __init__(self, ep_robot, config):
        # 1. Connect to the robot unit and chassis.
        self.ep_robot = ep_robot
        self.ep_chassis = ep_robot.chassis
        
        # 2. Retrieve values ​​from the configuration and store them in variables with easy-to-understand names.
        self.data_dir = config["data_collection"]["data_dir"]
        self.buffer_time = config["data_collection"]["buffer_time"]
        
        # Extract the frequency of each sensor.
        self.freq_pos = config["data_collection"]["frequencies"]["position"]
        self.freq_att = config["data_collection"]["frequencies"]["attitude"]
        self.freq_imu = config["data_collection"]["frequencies"]["imu"]
        self.freq_esc = config["data_collection"]["frequencies"]["esc"]
        
        # Retrieve motion-related values.
        self.default_speed = config["movement"]["xy_speed"]
        self.default_distance = config["movement"]["distance"]
        self.default_z_speed = config["movement"]["z_speed"] 
        self.default_angle = config["movement"]["angle"]   
        
        # 3. Create a folder to store the files (if one does not already exist, create a new one immediately).
        os.makedirs(self.data_dir, exist_ok=True)
        date_str = datetime.now().strftime("%Y%m%d")
        
        # Combine the date to form a filename in the format `log_yyyymmdd_sensorName.csv`.
        pos_name = f"log_{date_str}_{config['data_collection']['files']['position']}.csv"
        att_name = f"log_{date_str}_{config['data_collection']['files']['attitude']}.csv"
        imu_name = f"log_{date_str}_{config['data_collection']['files']['imu']}.csv"
        esc_name = f"log_{date_str}_{config['data_collection']['files']['esc']}.csv"

        # 4.Name the file paths for the four CSV files.
        self.pos_file = os.path.join(self.data_dir, pos_name)
        self.att_file = os.path.join(self.data_dir, att_name)
        self.imu_file = os.path.join(self.data_dir, imu_name)
        self.esc_file = os.path.join(self.data_dir, esc_name)

    # =========================================================
    # Part 1: Function for writing a CSV file and receiving a return value (Callback)
    # =========================================================
    def save_to_csv(self, filename, data):
        """A central function for appending data to a CSV file."""
        current_time = time.time()  # Capture the current time (Unix Timestamp)
        
        # Opening a file in 'a' (append) mode means writing to the end of the existing content.
        with open(filename, mode='a', newline='') as f:
            writer = csv.writer(f)
            
            # Place the time in the first column.
            row = [current_time]
            
            # Loop through the process of appending sensor data to the timestamp.
            for item in data:
                if isinstance(item, (list, tuple)):
                    row.extend(item)  # If the data is a list, expand it.
                else:
                    row.append(item)  # If it is a single value, you can simply append it.
                    
            writer.writerow(row)      # Save to file (1 row).

    # The data handler function immediately calls `save_to_csv` whenever the sensor sends a value.
    def handle_position(self, data):
        self.save_to_csv(self.pos_file, data)

    def handle_attitude(self, data):
        self.save_to_csv(self.att_file, data)

    def handle_imu(self, data):
        self.save_to_csv(self.imu_file, data)

    def handle_esc(self, data):
        self.save_to_csv(self.esc_file, data)

    # =========================================================
    # Part 2: Sensor Data Collection Management Function
    # =========================================================
    def setup_csv_headers(self):
        """Create a new CSV file and write the column headers."""
        with open(self.pos_file, mode='w', newline='') as f:
            csv.writer(f).writerow(["unix_timestamp", "x", "y", "z"])
            
        with open(self.att_file, mode='w', newline='') as f:
            csv.writer(f).writerow(["unix_timestamp", "yaw", "pitch", "roll"])
            
        with open(self.imu_file, mode='w', newline='') as f:
            csv.writer(f).writerow(["unix_timestamp", "acc_x", "acc_y", "acc_z", "gyro_x", "gyro_y", "gyro_z"])
            
        with open(self.esc_file, mode='w', newline='') as f:
            csv.writer(f).writerow(["unix_timestamp", "esc_data"])
        print("All four CSV files have been prepared.")

    def start_sensors(self):
        """Activate all sensors according to the frequency set in the configuration."""
        print("Starting to collect sensor data...")
        self.ep_chassis.sub_position(freq=self.freq_pos, callback=self.handle_position)
        self.ep_chassis.sub_attitude(freq=self.freq_att, callback=self.handle_attitude)
        self.ep_chassis.sub_imu(freq=self.freq_imu, callback=self.handle_imu)
        self.ep_chassis.sub_esc(freq=self.freq_esc, callback=self.handle_esc)

    def stop_sensors(self):
        """Disable all sensors."""
        time.sleep(self.buffer_time)  # Wait for the final set of data to finish saving.
        self.ep_chassis.unsub_position()
        self.ep_chassis.unsub_attitude()
        self.ep_chassis.unsub_imu()
        self.ep_chassis.unsub_esc()
        print("Data collection and saving to the file have been fully completed.")

    # =========================================================
    # Part 3: Motion Control Functions
    # =========================================================
    def move_forward(self, distance=None, speed=None):
        """Forward command: If no number is specified, the default value from the config will be used.
"""
        # If the distance value is not provided, use self.default_distance from the config.
        if distance is None:
            distance = self.default_distance
            
        if speed is None:
            speed = self.default_speed
            
        print(f"--> Robot moving forward {distance} meters (speed {speed} m/s)")
        self.ep_chassis.move(x=distance, y=0, z=0, xy_speed=speed).wait_for_completed()

    def move_backward(self, distance=None, speed=None):
        """Reverse command: If no number is specified, the default value from the config is used."""
        if distance is None:
            distance = self.default_distance
            
        if speed is None:
            speed = self.default_speed
            
        print(f"--> Robot is moving backward {distance} meters (speed {speed} m/s)")
        # Move backward by placing a negative sign (-distance) on the x-axis.
        self.ep_chassis.move(x=-distance, y=0, z=0, xy_speed=speed).wait_for_completed()

    def turn_left(self, angle=None, speed=None):
        """Left-turn command (counter-clockwise; uses a positive degree value)"""
        if angle is None:
            angle = self.default_angle
        if speed is None:
            speed = self.default_z_speed
            
        print(f"--> Robot is turning left by {angle} degrees (rotation speed: {speed} deg/s)")
        # To turn left, set the z-value to positive (+angle) and use the z_speed parameter.
        self.ep_chassis.move(x=0, y=0, z=angle, z_speed=speed).wait_for_completed()

    def turn_right(self, angle=None, speed=None):
        """Right-turn command (clockwise; represented by a negative angle value)"""
        if angle is None:
            angle = self.default_angle
        if speed is None:
            speed = self.default_z_speed
            
        print(f"--> Robot is turning right by {angle} degrees (rotation speed: {speed} deg/s)")
        # To turn right, you need to place a minus sign (-angle) on the z-axis.
        self.ep_chassis.move(x=0, y=0, z=-angle, z_speed=speed).wait_for_completed()

    def test_movement(self):
        """Movement test: Forward -> Backward -> Turn left -> Turn right and return to the starting point."""
        print("--- Starting mobility test ---")
        self.move_forward()
        
        time.sleep(1)  # Pause briefly before turning.
        
        self.turn_right()  # Make a 90-degree right turn and return to facing straight ahead.
        self.move_forward()

        time.sleep(1)  # Pause briefly before turning.

        self.turn_right()  # Make a 90-degree right turn and return to facing straight ahead.
        self.move_forward()
        
        time.sleep(1)  # Pause briefly before turning.
        self.turn_right()  # Make a 90-degree right turn and return to facing straight ahead.
        self.move_forward()
        
        time.sleep(1)  # Pause briefly before turning.
        self.turn_right()
        print("--- Movement complete ---")