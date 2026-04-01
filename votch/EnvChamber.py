#
# Methods to control a Weiss Gallenkamp environmental chamber
# controlled by SimPac controller
#
# David Cussans, Jeson Jacob, Bristol Sept 2011

import socket
import time

class EnvChamber(object):
    def __init__(self, address = "172.16.30.50" , port=2049 ):
        '''Create a socket and connect to the SimPac server '''
        self.sock = socket.socket(
            socket.AF_INET, socket.SOCK_STREAM)

        #now connect to the simpac server
        self.sock.connect((address, port))

        print("EnvChamber: connected to port %d on %s " % ( port , address ))

    def getTemp(self):
        '''Query the SimPac server and parse output
        to extract actual and set-point temperature '''

        #print "About to send"
        cmdString = "$01I\r"
        self.sock.sendall(cmdString.encode('utf-8'))

        #print "About to receive"

        buffsize=4096
        reply = self.sock.recv(buffsize).decode('utf-8')
        #reply = replyBytes.decode('utf-8')

        print ("reply = ", reply)

        fields = reply.split(" ")

        # Return set-point and actual temperature
        setPointField=0
        actualTempField=1
        return ( float(fields[setPointField]) , float(fields[actualTempField]) )

    def setTemp(self, temp ):
        '''Write the temperature set-point. Return immediately'''

        commandString = "$01E %06.1f 0000.0 0100.0 0000.0 0000.0 0000.0 0000.0 01101010101010101010101010101010\r" % float(temp)

        print("command string = " ,commandString)
        self.sock.sendall(commandString.encode('utf-8'))

        print("Sent command, about to receive")
        buffsize=4096
        reply = self.sock.recv(buffsize).decode('utf-8')

        print("received reply = " , reply)

        assert reply[0] == "0"
        
    def setTempWait( self, temperature, delta = 0.5 , pollingInterval = 60 ):
        '''Write the temperature set-point then wait until
        the temperature is within "delta" of the set-point before returning'''
    

        # First write the temperature set point....
        self.setTemp(temperature)

        print("Set temperature to " , temperature)

        actualDelta = 2*delta + 1.0 # put dummy value to start
        
        while ( abs(actualDelta) > delta ):
            
            time.sleep( pollingInterval )
            actualTemp = self.getTemp()[1]
            actualDelta = actualTemp - temperature

            print("actualTemp, actualDelta = ",  actualTemp, actualDelta)

        print("Setpoint reached. Temperature = " , actualTemp)

    def stop(self):
        '''Stop the environmental chamber. Use at the end of the data taking process (in SCurveData.py)'''
        
        commandString = "$01E 0020.0 0000.0 0100.0 0000.0 0000.0 0000.0 0000.0 00101010101010101010101010101010\r"

        
        self.sock.sendall(commandString.encode('utf-8'))
