        ep_robot.initialize()
        
        # 2. Initialize the chassis control class by passing in the configuration.
        chassis_ctrl = ChassisController(ep_robot, config)
        
        # 3. Workflow sequence (with clearly separated functions)
