import csv
import time
import os
import threading
from datetime import datetime


class ChassisController:
    def __init__(self, ep_robot, config):
        # 1. Connect to the robot unit, chassis, and sensors.
        self.ep_robot = ep_robot
        self.ep_chassis = ep_robot.chassis
        self.ep_sensor = ep_robot.sensor  # <-- NEW: Initialize the sensor module
        self.ep_sensor_adaptor = ep_robot.sensor_adaptor

        self.prev_ir1_cm = 30.0
        self.prev_ir2_cm = 30.0
        self.current_yaw = 0.0

        # 2. Retrieve values from the configuration.
        self.data_dir = config["data_collection"]["data_dir"]
        self.buffer_time = config["data_collection"]["buffer_time"]

        # Extract the frequency of each sensor.
        self.freq_pos = config["data_collection"]["frequencies"]["position"]
        self.freq_att = config["data_collection"]["frequencies"]["attitude"]
        self.freq_imu = config["data_collection"]["frequencies"]["imu"]
        self.freq_esc = config["data_collection"]["frequencies"]["esc"]
        self.freq_dist = config["data_collection"]["frequencies"][
            "distance"
        ]  # <-- NEW: Distance frequency

        # Retrieve motion-related values.
        self.default_speed = config["movement"]["xy_speed"]
        self.default_distance = config["movement"]["distance"]
        self.default_z_speed = config["movement"]["z_speed"]
        self.default_angle = config["movement"]["angle"]

        # 3. Create a folder to store the files.
        os.makedirs(self.data_dir, exist_ok=True)
        date_str = datetime.now().strftime("%Y%m%d")

        # Combine the date to form filenames.
        pos_name = (
            f"log_{date_str}_{config['data_collection']['files']['position']}.csv"
        )
        att_name = (
            f"log_{date_str}_{config['data_collection']['files']['attitude']}.csv"
        )
        imu_name = f"log_{date_str}_{config['data_collection']['files']['imu']}.csv"
        esc_name = f"log_{date_str}_{config['data_collection']['files']['esc']}.csv"
        dist_name = f"log_{date_str}_{config['data_collection']['files']['distance']}.csv"  # <-- NEW: Distance filename
        ir_name = f"log_{date_str}_{config['data_collection']['files']['infrared']}.csv"

        # 4. Name the file paths for the CSV files.
        self.pos_file = os.path.join(self.data_dir, pos_name)
        self.att_file = os.path.join(self.data_dir, att_name)
        self.imu_file = os.path.join(self.data_dir, imu_name)
        self.esc_file = os.path.join(self.data_dir, esc_name)
        self.dist_file = os.path.join(
            self.data_dir, dist_name
        )  # <-- NEW: Distance file path
        self.ir_file = os.path.join(self.data_dir, ir_name)

        # Variables for managing the IR sensor background thread
        self.is_logging_ir = False
        self.ir_thread = None

    # =========================================================
    # Part 1: Function for writing a CSV file and receiving a return value
    # =========================================================
    def save_to_csv(self, filename, data):
        """A central function for appending data to a CSV file."""
        current_time = time.time()
        with open(filename, mode="a", newline="") as f:
            writer = csv.writer(f)
            row = [current_time]
            for item in data:
                if isinstance(item, (list, tuple)):
                    row.extend(item)
                else:
                    row.append(item)
            writer.writerow(row)

    def handle_position(self, data):
        self.save_to_csv(self.pos_file, data)

    def handle_attitude(self, data):
        self.save_to_csv(self.att_file, data)
        self.current_yaw = data[0]

    def handle_imu(self, data):
        self.save_to_csv(self.imu_file, data)

    def handle_esc(self, data):
        self.save_to_csv(self.esc_file, data)

    def handle_distance(self, data):
        # <-- NEW: Callback for distance data
        self.save_to_csv(self.dist_file, data)
        self.current_tof_dist_mm = data[0]

    # =========================================================
    # Part 2: Sensor Data Collection Management Function
    # =========================================================
    def setup_csv_headers(self):
        """Create a new CSV file and write the column headers."""
        with open(self.pos_file, mode="w", newline="") as f:
            csv.writer(f).writerow(["unix_timestamp", "x", "y", "z"])

        with open(self.att_file, mode="w", newline="") as f:
            csv.writer(f).writerow(["unix_timestamp", "yaw", "pitch", "roll"])

        with open(self.imu_file, mode="w", newline="") as f:
            csv.writer(f).writerow(
                [
                    "unix_timestamp",
                    "acc_x",
                    "acc_y",
                    "acc_z",
                    "gyro_x",
                    "gyro_y",
                    "gyro_z",
                ]
            )

        with open(self.esc_file, mode="w", newline="") as f:
            csv.writer(f).writerow(["unix_timestamp", "esc_data"])

        with open(self.dist_file, mode="w", newline="") as f:
            # <-- NEW: Write headers for the 4 ToF sensors
            csv.writer(f).writerow(["unix_timestamp", "tof1"])

        with open(self.ir_file, mode="w", newline="") as f:
            csv.writer(f).writerow(
                ["unix_timestamp", "ir1_raw", "ir1_cm", "ir2_raw", "ir2_cm"]
            )

        print("All CSV files have been prepared.")

    def read_sharp_ir_sensor_1(self):
        """Polls the ADC port and logs the raw voltage data."""
        # Read the ADC value from the sensor adapter (id=1, port=1)
        adc_value = self.ep_sensor_adaptor.get_adc(id=2, port=1)
        # print(f"Sensor adapter id1-port1 ADC is {adc_value}")

        return adc_value

    def read_sharp_ir_sensor_2(self):
        """Polls the ADC port and logs the raw voltage data."""
        # Read the ADC value from the sensor adapter (id=1, port=1)
        adc_value = self.ep_sensor_adaptor.get_adc(id=1, port=2)
        # print(f"Sensor adapter id1-port2 ADC is {adc_value}")

        return adc_value

    def adc_to_cm(self, adc_value, C, prev_distance):
        """
        Converts the ADC reading to distance in centimeters.
        Note: ADC_MAX, M, and C require hardware-specific calibration.
        """

        if adc_value is None or adc_value <= 0:
            return -1.0

        # Assuming 10-bit ADC resolution (0-1023) and 3.3V maximum system voltage
        ADC_MAX = 1023.0
        SYSTEM_VOLTAGE = 3.3

        # 1. Convert ADC value back to voltage
        voltage = (adc_value / ADC_MAX) * SYSTEM_VOLTAGE

        # Prevent extremely low voltage (sensor reads > 30 cm, outside reliable range)
        if voltage < 0.4:
            return 30.0

        # 2. Calculate distance using the linear equation (Inverse characteristic)
        # Distance L is derived from V_o = M * (1 / (L + 0.42)) + C
        # The M (Slope) and C (Intercept) values below are estimates based on the datasheet
        M = 12.0

        distance_cm = (M / (voltage - C)) - 0.42

        if prev_distance < 6 and distance_cm > 8.0:
            return 3.0

        # Clamp the value to the 4 to 30 cm range based on sensor specifications
        if distance_cm < 4.0:
            return 4.0
        elif distance_cm > 30.0:
            return 30.0

        return round(distance_cm, 2)

    def _poll_ir_sensors(self):
        """Background thread task to continuously read and log IR sensors."""
        while self.is_logging_ir:
            try:
                # Read raw ADC values
                ir1_raw = self.read_sharp_ir_sensor_1()
                ir2_raw = self.read_sharp_ir_sensor_2()

                # Convert raw values to centimeters
                ir1_cm = self.adc_to_cm(ir1_raw,0, self.prev_ir1_cm)
                ir2_cm = self.adc_to_cm(ir2_raw,0, self.prev_ir2_cm)

                # Update previous distances
                self.prev_ir1_cm = ir1_cm
                self.prev_ir2_cm = ir2_cm

                # Save both raw and converted values to the single CSV file
                self.save_to_csv(self.ir_file, [ir1_raw, ir1_cm, ir2_raw, ir2_cm])

            except Exception as e:
                print(f"IR Logging Error: {e}")

            # Poll at approximately 10Hz (0.1 seconds) to match other sensor frequencies
            time.sleep(0.1)

    def start_sensors(self):
        """Activate all sensors according to the frequency set in the configuration."""
        print("Starting to collect sensor data...")
        self.ep_chassis.sub_position(freq=self.freq_pos, callback=self.handle_position)
        self.ep_chassis.sub_attitude(freq=self.freq_att, callback=self.handle_attitude)
        self.ep_chassis.sub_imu(freq=self.freq_imu, callback=self.handle_imu)
        self.ep_chassis.sub_esc(freq=self.freq_esc, callback=self.handle_esc)
        self.ep_sensor.sub_distance(
            freq=self.freq_dist, callback=self.handle_distance
        )  # <-- NEW: Start distance sensor

        # Start background thread for IR sensor polling
        self.is_logging_ir = True
        self.ir_thread = threading.Thread(target=self._poll_ir_sensors)
        self.ir_thread.daemon = True  # Ensure thread stops when main program exits
        self.ir_thread.start()

    def stop_sensors(self):
        """Disable all sensors."""
        time.sleep(self.buffer_time)
        self.ep_chassis.unsub_position()
        self.ep_chassis.unsub_attitude()
        self.ep_chassis.unsub_imu()
        self.ep_chassis.unsub_esc()
        self.ep_sensor.unsub_distance()  # <-- NEW: Stop distance sensor

        # Stop IR logging thread
        self.is_logging_ir = False
        if self.ir_thread is not None:
            self.ir_thread.join()

        print("Data collection and saving to the file have been fully completed.")

    # =========================================================
    # Part 3: Motion Control Functions
    # (Remains identical to your original code)
    # =========================================================
    
    def move_forward(self, distance=None, speed=None):
        if distance is None:
            distance = self.default_distance
        if speed is None:
            speed = self.default_speed
        print(f"--> Robot moving forward {distance} meters (speed {speed} m/s)")
        self.ep_chassis.move(x=distance, y=0, z=0, xy_speed=speed).wait_for_completed()

    def safe_move_forward(self, distance=0.6, speed=0.3, stop_limit_mm=175):
        """
        เดินหน้าแบบปลอดภัย คืนค่า True ถ้าย้ายสำเร็จ / False ถ้าเกิดเบรกฉุกเฉิน
        พร้อมระบบสไลด์รักษาระยะกึ่งกลางแบบ Real-time
        """
        print(f"--> [Safe Move] กำลังเดินหน้า {distance}m พร้อมรักษากึ่งกลาง...")
        travel_time = distance / speed
        start_time = time.time()

        current_y = 0.0
        ky = 0.2
        max_y = 0.05  # ปรับลดลงเพื่อไม่ให้หุ่นสะบัดสไลด์เร็วเกินไป
        alpha = 0.2
        
        # ใช้ลูปเดียว: เช็คเวลาเดิน ควบคู่กับเช็คเซนเซอร์ตลอดทาง
        while (time.time() - start_time) < travel_time:
            
            # 1. เช็คเบรกฉุกเฉิน (ToF)
            front_dist = self.current_tof_dist_mm
            if 0 < front_dist <= stop_limit_mm:
                print(f"!!! [เบรกฉุกเฉิน] เจอสิ่งกีดขวางระยะ {front_dist}mm หยุดการทำงาน !!!")
                self.ep_chassis.drive_speed(x=0, y=0, z=0)
                time.sleep(0.5)
                return True # แจ้งกลับไปว่าเดินไม่สำเร็จ

            # 2. อ่านค่า IR เพื่อสไลด์กึ่งกลาง
            ir1_cm = self.prev_ir1_cm
            ir2_cm = self.prev_ir2_cm
            
            if ir1_cm > 25:
                ir1_cm = 17.5
            if ir2_cm > 25:
                ir2_cm = 17.5
            
            target_y = (ir1_cm - ir2_cm) * ky
            
            # ป้องกันไม่ให้สไลด์เร็วเกินไป
            target_y = max(-max_y, min(max_y, target_y))
            
            # ทำ Smoothing เพื่อให้สไลด์เนียนขึ้น ไม่กระตุก
            current_y = (alpha * target_y) + ((1 - alpha) * current_y)
            
            # 3. สั่งหุ่นยนต์ให้เดินหน้าพร้อมสไลด์ข้าง (อัปเดตแบบ Real-time)
            self.ep_chassis.drive_speed(x=speed, y=current_y, z=0)
            
            # หน่วงเวลาสั้นๆ ก่อนคำนวณรอบถัดไป
            time.sleep(0.1)
            
        # เมื่อครบเวลาเดิน (ถึงเป้าหมาย 1 ช่อง) สั่งให้หุ่นหยุดนิ่ง
        self.ep_chassis.drive_speed(x=0, y=0, z=0)
        time.sleep(0.5)
        return True # เดินสำเร็จถึงเป้าหมาย
    
    def auto_drive_general(self, forward_speed=0.3, stop_threshold_mm=150):
        """
        ฟังก์ชันวิ่งรักษากึ่งกลาง พร้อมระบบ Safety Check กันชน
        """
        current_y = 0.0
        ky = 0.3
        max_y = 0.05
        alpha = 0.2
        SIDE_OPEN_CM = 20.0  

        while True:
            front_dist = self.current_tof_dist_mm
            left_dist = self.prev_ir2_cm
            right_dist = self.prev_ir1_cm
            
            # 1. Safety Check: เช็คระยะกำแพงหน้าก่อนเสมอ (เบรกที่ 30 ซม.)
            if 0 < front_dist <= stop_threshold_mm:
                self.ep_chassis.drive_speed(x=0, y=0, z=0)
                break
                
            # 2. เจอทางแยก (ซ้ายหรือขวาเปิดโล่ง)
            if right_dist > SIDE_OPEN_CM or left_dist > SIDE_OPEN_CM:
                self.ep_chassis.drive_speed(x=0, y=0, z=0)
                
                # ดันหุ่นไปข้างหน้า 15 ซม. เพื่อตั้งลำเลี้ยว 
                # *เซฟตี้: ทำได้ก็ต่อเมื่อข้างหน้าต้องมีที่ว่างมากกว่าระยะเบรก + 15 ซม.*
                if front_dist > (stop_threshold_mm + 150):
                    self.move_forward(0.15, speed=0.1) 
                break

            ir1_cm = self.prev_ir1_cm
            ir2_cm = self.prev_ir2_cm
                
            if ir1_cm > 25:
                ir1_cm = 17.5
            if ir2_cm > 25:
                ir2_cm =17.5

            target_y = (ir1_cm - ir2_cm) * ky

                # ป้องกันไม่ให้สไลด์เร็วเกินไป
            target_y = max(-max_y, min(max_y, target_y))
                
                # ทำ Smoothing เพื่อให้สไลด์เนียนขึ้น ไม่กระตุก
            current_y = (alpha * target_y) + ((1 - alpha) * current_y)

                # 4. สั่งหุ่นยนต์เดินหน้า (x) พร้อมสไลด์ข้าง (y) โดยไม่มีการหมุน (z=0)
                # **ข้อควรระวัง:** ทิศทาง +y หรือ -y ขึ้นอยู่กับระบบของหุ่น
                # ถ้าหุ่นสไลด์ผิดทาง (ยิ่งเข้าใกล้กำแพงยิ่งสไลด์ชน) ให้แก้สมการเป็น target_y = (ir2_cm - ir1_cm) * ky
            self.ep_chassis.drive_speed(x=forward_speed, y=current_y, z=0)
                
                # Delay
            time.sleep(0.01)

    def explore_and_map_all(self):
        """
        อัลกอริทึมทำแผนที่ 4x4 Grid (DFS) สำรวจ 100%
        เจอ Goal แล้วไม่หยุด จะถอยกลับไปสำรวจซอยที่เหลือจนกว่าจะครบ
        """
        print("--- เริ่มการสร้างแผนที่แบบสมบูรณ์ 4x4 Grid (DFS Mapping) ---")
        
        if not hasattr(self, 'current_tof_dist_mm'):
            self.current_tof_dist_mm = 10000 
            
        CELL_SIZE = 0.6       
        FRONT_WALL_MM = 300   
        SIDE_OPEN_CM = 25.0   

        visited = set()       
        stack = []            
        
        x, y = 0, 0
        heading = 0 # 0:N, 1:E, 2:S, 3:W
        moves = {0: (0, 1), 1: (1, 0), 2: (0, -1), 3: (-1, 0)}

        MAX_X = 3
        MAX_Y = 3
        
        goal_reached = False # ตัวแปรเช็คว่าเจอ Goal หรือยัง

        try:
            while True:
                self.ep_chassis.drive_speed(x=0, y=0, z=0)
                time.sleep(0.5) 
                
                visited.add((x, y))
                print(f"\n[Map] พิกัดปัจจุบัน: ({x}, {y}) หันหน้าทิศ: {heading}")
                
                # 💡 ถ้าเจอ Goal ให้แจ้งเตือน แต่ "ไม่ตัดจบโปรแกรม" เพื่อให้ไปสำรวจช่องอื่นต่อ
                if x == 3 and y == 0 and not goal_reached:
                    print("\n=== 🎉 ค้นพบจุด Goal (3,0) แล้ว! ระบบจะเดินสำรวจพื้นที่ส่วนที่เหลือต่อให้ครบ 100% ===")
                    goal_reached = True
                
                front_dist = self.current_tof_dist_mm
                right_dist = self.prev_ir1_cm  # IR 1 (ขวา)
                left_dist = self.prev_ir2_cm   # IR 2 (ซ้าย)
                
                open_dirs = []
                if front_dist > FRONT_WALL_MM:
                    open_dirs.append(heading)
                if right_dist > SIDE_OPEN_CM:
                    open_dirs.append((heading + 1) % 4)
                if left_dist > SIDE_OPEN_CM:
                    open_dirs.append((heading + 3) % 4)
                
                unvisited = []
                for d in open_dirs:
                    target_x = x + moves[d][0]
                    target_y = y + moves[d][1]
                    if 0 <= target_x <= MAX_X and 0 <= target_y <= MAX_Y:
                        if (target_x, target_y) not in visited:
                            unvisited.append(d)
                
                if unvisited:
                    next_heading = unvisited[0]
                    stack.append((x, y, heading))
                    
                    turn_angle = (next_heading - heading) * 90
                    if turn_angle > 180: turn_angle -= 360
                    if turn_angle < -180: turn_angle += 360
                    
                    print(f"-> เจอช่องว่าง! เลี้ยวทิศ {next_heading} (หมุน {turn_angle} องศา)")
                    
                    if turn_angle == 90:
                        self.turn_right(90)
                    elif turn_angle == -90:
                        self.turn_left(90)
                    elif abs(turn_angle) == 180:
                        self.turn_right(180)
                        
                    time.sleep(0.5) 
                    
                    if self.current_tof_dist_mm < 500:
                        print(f"-> [Double Check] ToF แจ้งว่าทางตัน มาร์คพิกัดนี้เป็นกำแพง!")
                        tx = x + moves[next_heading][0]
                        ty = y + moves[next_heading][1]
                        visited.add((tx, ty)) 
                        stack.pop() 
                        continue 
                        
                    success = self.safe_move_forward(distance=CELL_SIZE)
                    
                    if success:
                        x += moves[next_heading][0]
                        y += moves[next_heading][1]
                        heading = next_heading
                    else:
                        print("-> [Error] เกิดเบรกฉุกเฉิน ถอยกลับไปกลางกริดเดิม!")
                        tx = x + moves[next_heading][0]
                        ty = y + moves[next_heading][1]
                        visited.add((tx, ty))
                        stack.pop()
                        
                else:
                    # ถ้า Stack ว่างเปล่า แปลว่าสำรวจและถอยกลับมาจนถึงจุดเริ่มต้นแล้ว
                    if not stack:
                        print("\n=== สำรวจแผนที่ 4x4 ครบ 100% แล้ว! หุ่นยนต์หยุดทำงาน ===")
                        break
                        
                    prev_x, prev_y, prev_heading = stack.pop()
                    print(f"-> ทางตัน/สำรวจหมดแล้ว! ถอยกลับไปพิกัด ({prev_x}, {prev_y})")
                    
                    dx = prev_x - x
                    dy = prev_y - y
                    target_heading = 0
                    for h, m in moves.items():
                        if m == (dx, dy):
                            target_heading = h
                            break
                            
                    turn_angle = (target_heading - heading) * 90
                    if turn_angle > 180: turn_angle -= 360
                    if turn_angle < -180: turn_angle += 360
                    
                    if turn_angle == 90:
                        self.turn_right(90)
                    elif turn_angle == -90:
                        self.turn_left(90)
                    elif abs(turn_angle) == 180:
                        self.turn_right(180)
                        
                    self.safe_move_forward(distance=CELL_SIZE)
                    
                    x, y = prev_x, prev_y
                    heading = target_heading
                    
        except KeyboardInterrupt:
            print("\n--> ยกเลิกการสำรวจโดยผู้ใช้")
            self.ep_chassis.drive_speed(x=0, y=0, z=0)

    def move_backward(self, distance=None, speed=None):
        if distance is None:
            distance = self.default_distance
        if speed is None:
            speed = self.default_speed
        print(f"--> Robot is moving backward {distance} meters (speed {speed} m/s)")
        self.ep_chassis.move(x=-distance, y=0, z=0, xy_speed=speed).wait_for_completed()

    def turn_left(self, angle=None, speed=None):
        if angle is None:
            angle = self.default_angle
        if speed is None:
            speed = self.default_z_speed
        print(
            f"--> Robot is turning left by {angle} degrees (rotation speed: {speed} deg/s)"
        )
        self.ep_chassis.move(x=0, y=0, z=angle, z_speed=speed).wait_for_completed()

    def turn_right(self, angle=None, speed=None):
        if angle is None:
            angle = self.default_angle
        if speed is None:
            speed = self.default_z_speed
        print(
            f"--> Robot is turning right by {angle} degrees (rotation speed: {speed} deg/s)"
        )
        self.ep_chassis.move(x=0, y=0, z=-angle, z_speed=speed).wait_for_completed()

    def test_movement(self):
        print("--- Starting mobility test ---")
        
        self.auto_drive()
        time.sleep(0.5)
        self.turn_right()
        time.sleep(0.5)
        self.auto_drive(False, 2)
        time.sleep(0.5)
        self.auto_drive()
        time.sleep(0.5)
        self.turn_right()
        time.sleep(0.5)
        self.auto_drive()
        time.sleep(0.5)
        self.turn_right()
        time.sleep(0.5)
        self.move_forward(0.6,0.05)
        time.sleep(0.5)
        self.turn_right()
        time.sleep(0.5)
        self.auto_drive()
        time.sleep(0.5)
        self.ep_chassis.move(x=0, y=-0.215, z=0, xy_speed= 0.1).wait_for_completed()
        time.sleep(0.5)
        #self.auto_drive( , , , stop_threshold_mm=755)
        self.move_backward(0.755,0.05)
        
        print("--- Movement complete ---")
        