import sys
import os
import time
from robomaster import robot

# Add path for import module in src
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from src.config_loader import load_config
from src.chassis import ChassisController


def main():
    config = load_config("config/settings.yaml")
    ep_robot = robot.Robot()
    
    try:
        print("Connecting robot ....")
        ep_robot.initialize()
        
        chassis_ctrl = ChassisController(ep_robot, config)
        
        # 4. เปิดการทำงานและเริ่มบันทึกข้อมูลของเซนเซอร์ทั้งหมด
        chassis_ctrl.start_sensors()

        # หน่วงเวลาเล็กน้อย (1-2 วินาที) เพื่อให้เซนเซอร์ ToF และ IR ดึงค่าชุดแรกมาเก็บไว้ในตัวแปรก่อนเริ่มเดิน
        print("รอเซนเซอร์เริ่มทำงานและอ่านค่าชุดแรก...")
        time.sleep(2)

        # 5. เริ่มรันลำดับการเคลื่อนที่ (Auto Drive -> Turn Right -> Auto Drive)
        chassis_ctrl.test_movement()
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        ep_robot.close()
        print("Robot connection closed successfully.")

if __name__ == '__main__':
    main()