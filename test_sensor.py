from robomaster import robot
import time

if __name__ == '__main__':
    ep_robot = robot.Robot()
    ep_robot.initialize(conn_type="ap")
    while True:
        ep_sensor_adaptor = ep_robot.sensor_adaptor

        adc = ep_sensor_adaptor.get_adc(id=1 ,port=2)
        bcd = ep_sensor_adaptor.get_adc(id=2 ,port=1)
        print("sensor adapter L adc is {0}".format(adc),"sensor adapter R adc is {0}".format(bcd))
        time.sleep(0.1)
    ep_robot.close()
