#from connectStepper import send_serial_command

#send_serial_command('COM4',30)

from control_laser import control_laser

control_laser("98250937",turn_on=False)

