import os
import glob
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator

def get_latest_file(data_dir, pattern):
    """ฟังก์ชันค้นหาไฟล์ล่าสุดในโฟลเดอร์ตาม pattern"""
    files = glob.glob(os.path.join(data_dir, pattern))
    if not files: return None
    return max(files, key=os.path.getctime)

def plot_grid_map(data_dir):
    # 1. ค้นหาไฟล์ข้อมูลทั้งหมดที่เกี่ยวข้อง
    pos_file = get_latest_file(data_dir, '*position_data*.csv')
    att_file = get_latest_file(data_dir, '*attitude_data*.csv')
    tof_file = get_latest_file(data_dir, '*tof_data*.csv')
    ir_file = get_latest_file(data_dir, '*ir_data*.csv')

    if not pos_file or not att_file:
        print("ไม่พบไฟล์ Position หรือ Attitude ข้อมูลไม่เพียงพอต่อการสร้างแผนที่")
        return

    print("กำลังประมวลผลข้อมูลเพื่อสร้าง Grid Map...")

    # 2. อ่านข้อมูลและเรียงตามเวลา พร้อมบังคับชนิดข้อมูลเป็น float
    df_pos = pd.read_csv(pos_file)
    df_pos['unix_timestamp'] = df_pos['unix_timestamp'].astype(float)
    df_pos = df_pos.sort_values('unix_timestamp')
    
    df_att = pd.read_csv(att_file)
    df_att['unix_timestamp'] = df_att['unix_timestamp'].astype(float)
    df_att = df_att.sort_values('unix_timestamp')
    
    # รวมข้อมูลพิกัดและมุมหันหน้าเข้าด้วยกัน
    df_map = pd.merge_asof(df_pos, df_att, on='unix_timestamp', direction='nearest')

    # รวมข้อมูลเซนเซอร์ ToF (ด้านหน้า)
    if tof_file:
        df_tof = pd.read_csv(tof_file)
        df_tof['unix_timestamp'] = df_tof['unix_timestamp'].astype(float)
        df_tof = df_tof.sort_values('unix_timestamp')
        df_map = pd.merge_asof(df_map, df_tof, on='unix_timestamp', direction='nearest')
    
    # รวมข้อมูลเซนเซอร์ IR (ซ้าย-ขวา)
    if ir_file:
        df_ir = pd.read_csv(ir_file)
        df_ir['unix_timestamp'] = df_ir['unix_timestamp'].astype(float)
        df_ir = df_ir.sort_values('unix_timestamp')
        df_map = pd.merge_asof(df_map, df_ir, on='unix_timestamp', direction='nearest')

    # 3. คำนวณพิกัดของกำแพง
    wall_x, wall_y = [], []

    for idx, row in df_map.iterrows():
        rx = row['x']
        ry = row['y']
        
        # แปลงมุม Yaw จากองศาเป็นเรเดียน
        yaw_rad = np.radians(row['yaw']) if 'yaw' in row else 0.0

        # คำนวณกำแพงด้านหน้า (ToF1) - หน่วยเป็น mm แปลงเป็น m
        if 'tof1' in row and pd.notna(row['tof1']) and 0 < row['tof1'] < 2000:
            dist_m = row['tof1'] / 1000.0
            wall_x.append(rx + dist_m * np.cos(yaw_rad))
            wall_y.append(ry + dist_m * np.sin(yaw_rad))

        # คำนวณกำแพงซ้าย (IR1) - หน่วยเป็น cm แปลงเป็น m (สมมติทำมุม +90 องศาจากด้านหน้า)
        if 'ir1_cm' in row and pd.notna(row['ir1_cm']) and row['ir1_cm'] < 30.0:
            dist_m = row['ir1_cm'] / 100.0
            wall_x.append(rx + dist_m * np.cos(yaw_rad + np.pi/2))
            wall_y.append(ry + dist_m * np.sin(yaw_rad + np.pi/2))

        # คำนวณกำแพงขวา (IR2) - หน่วยเป็น cm แปลงเป็น m (สมมติทำมุม -90 องศาจากด้านหน้า)
        if 'ir2_cm' in row and pd.notna(row['ir2_cm']) and row['ir2_cm'] < 30.0:
            dist_m = row['ir2_cm'] / 100.0
            wall_x.append(rx + dist_m * np.cos(yaw_rad - np.pi/2))
            wall_y.append(ry + dist_m * np.sin(yaw_rad - np.pi/2))

    # 4. วาดกราฟ Grid Map
    fig, ax = plt.subplots(figsize=(10, 10))
    
    # วาดเส้นทางการเดินของหุ่นยนต์
    ax.plot(df_map['x'], df_map['y'], label='Robot Path', color='blue', linewidth=2, zorder=2)
    ax.plot(df_map['x'].iloc[0], df_map['y'].iloc[0], 'go', label='Start', markersize=10, zorder=3)
    ax.plot(df_map['x'].iloc[-1], df_map['y'].iloc[-1], 'ro', label='End', markersize=10, zorder=3)

    # วาดกำแพง (Obstacles)
    if wall_x:
        ax.scatter(wall_x, wall_y, color='black', s=20, label='Walls (Obstacles)', marker='s', zorder=1)

    # 5. ตกแต่งให้เป็นแผนที่ Grid แบบ 2D
    ax.set_title('RoboMaster Occupancy Grid Map with Walls')
    ax.set_xlabel('X (meters)')
    ax.set_ylabel('Y (meters)')
    
    # ตั้งค่าตารางกริด (Grid) ช่องหลักทุก 0.5m, ช่องย่อยทุก 0.1m
    ax.xaxis.set_major_locator(MultipleLocator(0.5))
    ax.xaxis.set_minor_locator(MultipleLocator(0.1))
    ax.yaxis.set_major_locator(MultipleLocator(0.5))
    ax.yaxis.set_minor_locator(MultipleLocator(0.1))
    
    ax.grid(which='major', color='gray', linestyle='-', linewidth=0.8)
    ax.grid(which='minor', color='lightgray', linestyle=':', linewidth=0.5)
    
    ax.set_aspect('equal') # รักษาสัดส่วน 1:1 ป้องกันกราฟเบี้ยว
    ax.legend(loc='upper right')
    ax.invert_xaxis()

    # บันทึกรูปภาพ
    output_img = os.path.join(data_dir, 'grid_map_with_walls.png')
    plt.savefig(output_img, dpi=300, bbox_inches='tight')
    print(f"บันทึกรูปแผนที่สำเร็จ: {output_img}")
    
    plt.show()

if __name__ == "__main__":
    # ระบุเส้นทางไปยังโฟลเดอร์เก็บข้อมูล
    target_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'raw', 'run1'))
    plot_grid_map(target_dir)