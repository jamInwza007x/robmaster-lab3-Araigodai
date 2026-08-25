import sys
import os
import time
from robomaster import robot

# Add path for import module in src
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

        arm_gripper_ctrl.reset_position()
        arm_gripper_ctrl.pick_up_object(x_dist=60, y_dist=-20, power=50)

        # 5. เริ่มรันลำดับการเคลื่อนที่ (Auto Drive -> Turn Right -> Auto Drive)
        chassis_ctrl.test_movement()

        chassis_ctrl.move_backward(0.1,0.1)

        arm_gripper_ctrl.release_object(power=50)
        arm_gripper_ctrl.reset_position()
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        ep_robot.close()
        print("Robot connection closed successfully.")

if __name__ == '__main__':
    main()