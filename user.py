'''
Created on 06-Nov-2018

@author: arunabha
'''

import datetime
import random
import socket
import time

from Crypto.PublicKey import RSA

from AESCipher import sendAESData, decryptAESData
from HashGenerator import getHash
from RSAencryption import sendData, generateRSAkey, decryptMsg
from diffiehellman import getDHkey
from diffiehellman import getSessionKey
from AESCipher import getAESRandSessionKey
from signature import signData


def exchangePublicKey(server, userPbKey):
    key = ""
    try:
        temp = server.recv(1024)
        if temp != "":
            print "Broker Pb Key + hash received from Broker"
            print temp
            data = temp.split(";")[0]
            dataHash = temp.split(";")[1]
            if getHash(data) == dataHash:
                server.send(userPbKey + ";" + getHash(userPbKey))
                print ("Broker public key hash recieved by User")
                key = data
            else:
                print "Broker Public Key Hash doesn't match"
    except Exception as e:
        print "Unable to get broker public key"
        print e
    return key

def connectBroker(server, brokerSessionKey, prkey, prDHkey):
    flag = True
    inp = raw_input("Enter the Seller IP address & port (format:-ipaddress:port): ")
    sendAESData(inp, server, brokerSessionKey)
    sellerPbKey = server.recv(1024)
    print "Received Seller key in User"
    print sellerPbKey
    userSellerkey = generateRSAkey()
    userSellerPbkey = userSellerkey.publickey().exportKey()
    userSellerPrkey = userSellerkey.exportKey()
    #sendData(str(userSellerPbkey), server, sellerPbKey)
    server.send(userSellerPbkey)
    time.sleep(0.1)
    sellerNounce = decryptMsg(server.recv(2048), userSellerPrkey)
    prDHKey = random.randint(100,1000)
    sendData(getDHkey(prDHKey), server, sellerPbKey)
    randUserSellerNounce = getSessionKey(sellerNounce, prDHKey)
    sellerSessionKey = getHash(randUserSellerNounce)
    rep = True
    while rep:
        randUserSellerNounce = int(randUserSellerNounce)+1                    
        broucher = decryptAESData(server, getAESRandSessionKey(sellerSessionKey,randUserSellerNounce))
        print broucher
        inp = raw_input("Choose any product by its Serial Number: ")
        inpflag = False
        while inpflag == False:
            if(int(inp) > 4 or int(inp) < 1):
                print "Invalid Input. Try again" 
                inp = raw_input("Choose any product by its Serial Number: ")
            else:
                inpflag = True 
        randUserSellerNounce = int(randUserSellerNounce)+1
        sendAESData(inp, server, getAESRandSessionKey(sellerSessionKey,randUserSellerNounce))
        randUserSellerNounce = int(randUserSellerNounce)+1
        price = decryptAESData(server, getAESRandSessionKey(sellerSessionKey,randUserSellerNounce))
        print "Price of the product you want to buy is $" + str(price)
        inp = raw_input("Are you sure you want to buy? [Y/N]: ")
        dbTransact = str(price)
        sign = signData(dbTransact, prkey)
        if inp.upper() == "Y":
            sendAESData(dbTransact+"~"+sign, server, brokerSessionKey)
            randUserSellerNounce = int(randUserSellerNounce)+1
            imageString = decryptAESData(server, getAESRandSessionKey(sellerSessionKey,randUserSellerNounce))
            output_file = open("Output/output_buyer"+str(random.randint(10,1000))+".jpg", "wb")
            output_file.write(imageString.decode('base64'))
            output_file.close()
            randUserSellerNounce = int(randUserSellerNounce)+1
            msg = decryptAESData(server, getAESRandSessionKey(sellerSessionKey,randUserSellerNounce))
            print msg
            inp = raw_input("Press Y to continue else press N: ")
            if inp.upper() != "Y":
                rep = False
                inp = raw_input("Do you want to connect another seller [Y/N]: ")
                if inp.upper() != "Y":
                    flag = False
                    print "Bye!"
                    add = RSA.importKey(sellerPbKey).encrypt("N",32)
                    sendAESData("quit:B"+str(add), server, brokerSessionKey)
                else:
                    add = RSA.importKey(sellerPbKey).encrypt("N",32)
                    data = "broker:B"+str(add)
                    sendAESData(data, server, brokerSessionKey)                        
            else:
                add = RSA.importKey(sellerPbKey).encrypt("Y",32)
                data = "seller:B"+str(add)
                sendAESData(data, server, brokerSessionKey)
        else:
            sendData("No Purchase", server, prkey)
    return flag
    
class User:
    def __init__(self,ip,port):
        try:
            flag = True
            pukeyFile = open('User/public_key.pem', 'rb')
            prkeyFile = open('User/private_key.pem', 'rb')
            self.pukey = pukeyFile.read()
            self.prkey = prkeyFile.read()
            pukeyFile.close()
            prkeyFile.close()
            #generating DH keys
            prDHKey = random.randint(100,1000)
            #Setting up socket
            server = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
            server.connect((ip,int(port)))
            server.send("User")
            brokerPbKey = exchangePublicKey(server, self.pukey)
            if brokerPbKey:
                print "User - Broker Key exchange successful"
                #Diffie-Hellman Key Exchange Starts here
                sendData(getDHkey(prDHKey), server, brokerPbKey)
                data = decryptMsg(server.recv(1024), self.prkey)
                brokerSessionKey = getSessionKey(data, prDHKey)
                brokerSessionKey = getHash(brokerSessionKey)
                print "DH Authentication successful"    
                while flag:
                    flag = connectBroker(server, brokerSessionKey, self.prkey, prDHKey)
            else:
                print "Issue in broker key"
        except Exception as e:
            print e
