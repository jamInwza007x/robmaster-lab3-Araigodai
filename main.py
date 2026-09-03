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
from src.gimbal_lidar import GimbalLidarController


def main():
    config = load_config("config/settings.yaml")
    ep_robot = robot.Robot()

    
    try:
        ep_robot.initialize(conn_type="ap")
        chassis_ctrl = ChassisController(ep_robot, config)
        lidar_ctrl = GimbalLidarController(ep_robot, config)

        print("\n=== ทำการสแกน 2D LiDAR Scan (ปิด Background Thread ระหว่างสแกน) ===")
        scan_data = lidar_ctrl.scan()
        if scan_data:
            lidar_ctrl.save_to_csv(scan_data)
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        ep_robot.close()
        print("Robot connection closed successfully.")

if __name__ == '__main__':
    main()