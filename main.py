import sys
import os
import time
from robomaster import robot

# Add path for import module in src
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from src.config_loader import load_config
from src.chassis import ChassisController

# ตัวแปร Global แบบ List สำหรับอัปเดตข้อมูลแบบเรียลไทม์
current_tof_dist_mm = [9999]
current_ir1_cm = [30.0]  # เก็บค่า IR ขวาล่าสุด
current_ir2_cm = [30.0]

def run_wall_follower(ep_robot, chassis_ctrl):
    """
    ฟังก์ชันสำหรับเดินตามกำแพงขวาที่ระยะ 10 cm 
    และหยุดเมื่อเจอสิ่งกีดขวางด้านหน้า
    """
    ep_chassis = ep_robot.chassis
    
    forward_speed = 0.1       # ความเร็วเดินหน้า (เมตร/วินาที)
    stop_threshold_mm = 55    # ระยะ ToF สำหรับหยุด 5 cm (50 mm)


    print("--> เริ่มทำงาน: เดินตามกำแพงขวาที่ระยะ 10 cm...")

    try:
        while True:
            # 1. ตรวจสอบสิ่งกีดขวางด้านหน้า (ToF)
            # ป้องกันค่า 0 หรือค่าที่ผิดพลาด (สมมติว่าค่า 0 คือ error)
            tof_dist = current_tof_dist_mm[0]
            if 0 < tof_dist <= stop_threshold_mm:
                print(f"--> เจอสิ่งกีดขวางด้านหน้า! (ระยะ {tof_dist} mm) -> หยุดหุ่นยนต์")
                ep_chassis.drive_speed(x=0, y=0, z=0)
                break

            # 2. ดึงค่า IR1 (ขวา) แบบไม่อ่านซ้ำซ้อนจากฮาร์ดแวร์
            ir1_cm = current_ir1_cm[0]
            ir2_cm = current_ir2_cm[0]

            # 3. คำนวณความเร็วในการหมุน Z ด้วย PD Controller
            if ir1_cm >= 16.0:
                # ถ้าเซนเซอร์มองไม่เห็นกำแพง ให้หุ่นเลี้ยวขวาเบาๆ เพื่อหากำแพง
                z_speed = 10.0
            else:
                z_speed = -10.0

            if ir2_cm >= 16.0:
                z_speed = -10.0
            else:
                z_speed = 10.0
            

            # 4. สั่งหุ่นยนต์เดินหน้าพร้อมประคองเลี้ยวอย่างต่อเนื่อง
            ep_chassis.drive_speed(x=forward_speed, y=0, z=z_speed)
            
            # ปรับเป็น 0.05 (20Hz) เพื่อให้รับคำสั่งได้เนียนและลื่นไหลขึ้น
            time.sleep(0.05)

    except KeyboardInterrupt:
        print("--> ยกเลิกการทำงานโดยผู้ใช้")
    finally:
        ep_chassis.drive_speed(x=0, y=0, z=0)
        print("--> ปิดการทำงาน Wall Following")

def main():
    config = load_config("config/settings.yaml")
    ep_robot = robot.Robot()
    
    try:
        print("Connecting robot ....")
        ep_robot.initialize()
        
        chassis_ctrl = ChassisController(ep_robot, config)
        
        # --- [ส่วนที่ 1] Intercept Callback ของ ToF ---
        original_tof_callback = chassis_ctrl.handle_distance 
        def custom_tof_callback(sub_info):
            current_tof_dist_mm[0] = sub_info[0]
            original_tof_callback(sub_info)
        chassis_ctrl.handle_distance = custom_tof_callback
        
        # --- [ส่วนที่ 2] Intercept การบันทึกค่าของ IR Sensor ---
        # ป้องกันปัญหา Thread ชนกันที่ทำให้บอร์ดค้าง 
        original_save_to_csv = chassis_ctrl.save_to_csv
        def custom_save_to_csv(filename, data):
            if filename == chassis_ctrl.ir_file:
                # ข้อมูลส่งมาเป็น: [ir1_raw, ir1_cm, ir2_raw, ir2_cm]
                current_ir1_cm[0] = data[1] # ดึงค่า ir1_cm มาอัปเดตให้ลูปหลักใช้งาน
                current_ir2_cm[0] = data[3]
            original_save_to_csv(filename, data)
        chassis_ctrl.save_to_csv = custom_save_to_csv
        # --------------------------------------------------

        chassis_ctrl.setup_csv_headers()
        chassis_ctrl.start_sensors()
        
        # รอให้เซนเซอร์ทั้งหมดส่งค่าแรกมาก่อนเริ่มคำนวณ
        time.sleep(1)
        
        # รันระบบ Wall Following
        run_wall_follower(ep_robot, chassis_ctrl)
        
        chassis_ctrl.stop_sensors()
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        ep_robot.close()
        print("Robot connection closed successfully.")

if __name__ == '__main__':
    main()