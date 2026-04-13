#!/usr/bin/env python
#
# Exercise EnvChamber library
#
import EnvChamber

 

chamber = EnvChamber.EnvChamber(address = "10.70.31.113")



temperature = chamber.getTemp()[1]

print ("Temperature measured = ",temperature)

#setPoint = temperature - 10
setPoint = temperature  - 2

# Set temperature and wait until it gets to within "delta" of the target

chamber.setTempWait(temperature=setPoint , delta = 1.0 )

print ("setTempWait has finished. Temperature = ", chamber.getTemp()[1])

print ("Stopping test")
chamber.stop()
