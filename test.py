from robomaster import robot
import csv
import time

# กำหนดชื่อไฟล์ CSV สำหรับเซ็นเซอร์ทั้ง 4 แบบ
POS_FILE = "position_data.csv"
ATT_FILE = "attitude_data.csv"
IMU_FILE = "imu_data.csv"
ESC_FILE = "esc_data.csv"

# ฟังก์ชันส่วนกลางสำหรับรับค่าแล้วเขียนลงไฟล์
def write_to_csv(filename, data):
    # ใช้ time.time() เพื่อรับค่า Unix Timestamp (เป็นวินาทีทศนิยม)
    unix_timestamp = time.time()
    
    # เปิดไฟล์แบบ 'a' (Append) เพื่อเขียนต่อท้ายไปเรื่อยๆ
    with open(filename, mode='a', newline='') as f:
        writer = csv.writer(f)
        
        # เริ่มต้นแถวด้วย Timestamp
        row = [unix_timestamp]
        
        # กระจายข้อมูลจากเซ็นเซอร์ (Flatten) ให้อยู่ในแถวเดียวกัน
        for item in data:
            if isinstance(item, (list, tuple)):
                row.extend(item)
            else:
                row.append(item)
                
        writer.writerow(row)

# แยก Callback Handler สำหรับแต่ละเซ็นเซอร์
def sub_pos_handler(position_info):
    write_to_csv(POS_FILE, position_info)

def sub_att_handler(attitude_info):
    write_to_csv(ATT_FILE, attitude_info)

def sub_imu_handler(imu_info):
    write_to_csv(IMU_FILE, imu_info)

def sub_esc_handler(esc_info):
    write_to_csv(ESC_FILE, esc_info)

def init_csv_headers():
    # ฟังก์ชันสำหรับเตรียมไฟล์และเขียนหัวคอลัมน์ (Headers) ก่อนเริ่มดึงข้อมูล
    with open(POS_FILE, mode='w', newline='') as f:
        csv.writer(f).writerow(["unix_timestamp", "x", "y", "z"])
    with open(ATT_FILE, mode='w', newline='') as f:
        csv.writer(f).writerow(["unix_timestamp", "yaw", "pitch", "roll"])
    with open(IMU_FILE, mode='w', newline='') as f:
        csv.writer(f).writerow(["unix_timestamp", "acc_x", "acc_y", "acc_z", "gyro_x", "gyro_y", "gyro_z"])
    with open(ESC_FILE, mode='w', newline='') as f:
        csv.writer(f).writerow(["unix_timestamp", "esc_data"]) # ข้อมูล ESC ของทั้ง 4 มอเตอร์จะถูกต่อกันยาว

if __name__ == '__main__':
    # สร้างไฟล์และเขียน Headers ก่อนรัน
    init_csv_headers()

    ep_robot = robot.Robot()
    ep_robot.initialize(conn_type="ap")
    
    ep_chassis = ep_robot.chassis

    print("เริ่มการเก็บข้อมูล...")

    # สมัครรับข้อมูลจากเซ็นเซอร์ โดยเรียกใช้ handler ที่แยกไว้
    ep_chassis.sub_position(freq=1, callback=sub_pos_handler)
    ep_chassis.sub_attitude(freq=5, callback=sub_att_handler)
    ep_chassis.sub_imu(freq=10, callback=sub_imu_handler)
    ep_chassis.sub_esc(freq=20, callback=sub_esc_handler)

    # เดินหน้า 0.3 เมตร
    ep_chassis.move(x=0.3, y=0, z=0, xy_speed=0.1).wait_for_completed()

    # ถอยหลัง 0.3 เมตร
    ep_chassis.move(x=-0.3, y=0, z=0, xy_speed=0.1).wait_for_completed()
    
    # เผื่อเวลาให้เก็บข้อมูลที่ค้างอยู่เล็กน้อย
    time.sleep(0.5)

    # ยกเลิกการ subscribe ข้อมูลเมื่อทำงานเสร็จ
    ep_chassis.unsub_position()
    ep_chassis.unsub_attitude()
    ep_chassis.unsub_imu()
    ep_chassis.unsub_esc()

    ep_robot.close()
    print("เก็บข้อมูลเสร็จสิ้นและบันทึกลง 4 ไฟล์เรียบร้อยแล้ว")