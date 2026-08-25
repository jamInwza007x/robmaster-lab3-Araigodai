from robomaster import robot


if __name__ == '__main__':
    ep_robot = robot.Robot()
    ep_robot.initialize(conn_type="ap")

    ep_sensor_adaptor = ep_robot.sensor_adaptor

    adc = ep_sensor_adaptor.get_adc(id=2, port=1)
    print("sensor adapter id1-port1 adc is {0}".format(adc))
    ep_robot.close()
