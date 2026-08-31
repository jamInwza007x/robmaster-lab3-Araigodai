import sys
import os
import time
from robomaster import robot

# Add path for import module in src
sys.path.append(os.path.dirname(os.path.abspath(__file__)))   
sys.path.append(os.path.dirname(os.path.abspath(__file__)))   
from src.config_loader import load_config
from src.chassis import ChassisController
from src.arm_gripper import ArmGripperController


def main():
    config = load_config("config/settings.yaml")
    ep_robot = robot.Robot()
    
    
    try:
        print("Connecting robot ....")
        ep_robot.initialize()
        
        chassis_ctrl = ChassisController(ep_robot, config)
        arm_gripper_ctrl = ArmGripperController(ep_robot)

        chassis_ctrl.start_sensors()
        chassis_ctrl.setup_csv_headers()

        # หน่วงเวลาเล็กน้อย (1-2 วินาที) เพื่อให้เซนเซอร์ ToF และ IR ดึงค่าชุดแรกมาเก็บไว้ในตัวแปรก่อนเริ่มเดิน
        print("รอเซนเซอร์เริ่มทำงานและอ่านค่าชุดแรก...")
        time.sleep(2)

        chassis_ctrl.explore_and_map_all()
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        ep_robot.close()
        print("Robot connection closed successfully.")

if __name__ == '__main__':
    main()