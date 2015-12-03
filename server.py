#!/usr/bin/env python


import SocketServer 
from SocketServer import ThreadingMixIn
import threading 
import socket
import time
from Queue import Queue
import sys
import os
from threading import Lock
import select
import pdb
import collections

client_connections={}
chatroom={}	
user_status={} # 1 == online and 0 == offline
user_cached_messages={}
mutex = Lock()
authorization_token={}
join_id=0

class ThreadingPoolMixIn(ThreadingMixIn):
    numThreads=60;  
    def serve_forever(self):
        print "Server Starting..."
        self.queue = Queue(self.numThreads)
        for x in range(self.numThreads):
            server_thread = threading.Thread(target = self.process_request_thread)
            server_thread.daemon = True
            server_thread.start()
        while True:
            self.handle_request()
        self.server_close()
   
    def process_request_thread(self):
        while True:
            ThreadingMixIn.process_request_thread(self, *self.queue.get())
               
    def handle_request(self):
        # Look after request
        request, client_address = self.get_request()
        print request.gettimeout()
        self.queue.put((request, client_address))
        

    		
    		            
class ThreadedTCPRequestHandler(SocketServer.BaseRequestHandler):
     
     def handle(self):
        while True:
            print "New Query...";
            print self.request
            global mutex
            self.request.setblocking(0)
            timeout_in_seconds=1
            data = ''
            while "\n\n" not in data:
                ready = select.select([self.request], [], [], timeout_in_seconds)
                if ready[0]:
                    d = self.request.recv(4096)
                    data += d
                    if len(d) < 4096:
                        break
                #else:
                #    data=""
            #if data =='':
            #    print "Socket Timeout, closing socket..."
            #    break
            print data
            # Assignment 1
            if data == "KILL_SERVICE\n":
                #mutex.release()	
                print "Killing server..."
                os._exit(0) 	    	
            elif data.startswith("HELO") and data.endswith("\n"):
                #mutex.release()
                print "Helo..."
                ip, port = server.server_address
                response= data+"IP:"+"52.91.13.50"+"\nPort:"+str(port)    +"\nStudentID:d70070b538a25d809c0ee6e1dc652d27c400edf1c4a64aee11cfd9269eacd474"   		
                self.request.sendall(response)
            #Assignment 2
            elif data.startswith("JOIN_CHATROOM:"):
                print "Joining chatroom..."
                #mutex.acquire()
                #global join_id
                #new_join_id=join_id
                #join_id = join_id+1
                client_name=input_parser(data,"CLIENT_NAME:")
                client_name = client_name.strip(' \t\n\r')
                join_id=str(hash(client_name))
                #mutex.release()	
                connection(self.request,data,join_id)
                join_chatroom(data)
            	
            elif data.startswith("LEAVE_CHATROOM:"):
            #	pdb.set_trace()
                print "LEAVE"
                ##mutex.release()	
                leave_chatroom(data)
            elif data.startswith("CHAT:"):
                #mutex.release()	
                send_message(data)
            elif data.startswith("DISCONNECT:"):
                disconnecting(self.request,data)
                
                
            

def response_join(data):
    print "Responding to join..."
    JOINED_CHATROOM = input_parser(data,"JOIN_CHATROOM:")
    JOINED_CHATROOM = JOINED_CHATROOM.strip(' \t\n\r')
    SERVER_IP,PORT=server.server_address
    ROOM_REF=  sum([(ord(n)-ord('0')) * (10 ** i) for i,n in enumerate(reversed(JOINED_CHATROOM))])
    client_name=input_parser(data,"CLIENT_NAME:")
    client_name = client_name.strip(' \t\n\r')
    JOIN_ID= str(hash(client_name))#authorization_token[client_name]
    message= "JOINED_CHATROOM:"+JOINED_CHATROOM +"\nSERVER_IP:"+str(SERVER_IP) +"\nPORT:"+str(PORT)+"\nROOM_REF:"+str(ROOM_REF)+"\nJOIN_ID:"+str(JOIN_ID)+"\n"
    print client_connections[client_name]
    client_connections[client_name].sendall(message)    
def response_leave(data):	
    print "Responding to leave..."
    LEFT_CHATROOM = input_parser(data,"LEAVE_CHATROOM: ")
    client_name=input_parser(data,"CLIENT_NAME: ")
    JOIN_ID=str(hash(client_name))# authorization_token[client_name]	
    message= "LEFT_CHATROOM:"+LEFT_CHATROOM+"\n"+"JOIN_ID:"+str(JOIN_ID)+"\n"
    client_connections[client_name].sendall(message)  	    

def connection(request,data,auth):
	client_name=input_parser(data,"CLIENT_NAME:")
	client_name = client_name.strip(' \t\n\r')
	global mutex
	mutex.acquire()
	try:
		client_connections[client_name]=request
		user_status[client_name]=1
		authorization_token[client_name]=auth
	finally:
		mutex.release()

def disconnecting(request,data):
	client_name=input_parser(data,"CLIENT_NAME:")
	client_name = client_name.strip(' \t\n\r')
	global mutex
	mutex.acquire()
	global chatroom
	chatroom=collections.OrderedDict(sorted(chatroom.items()))
	try:
		for chatroom_id,clients in chatroom.iteritems():
		    if client_name in clients:
		        print "Client in disconnecting"
		        print clients 
		        print chatroom_id
		        message=client_name+" has left this chatroom."
		        #message="client1 has left this chatroom."
		        mutex.release()	
		        multicast_chatroom(chatroom_id,message,client_name)
		        mutex.acquire()
		        clients.remove(client_name)
	finally:
		mutex.release()
		request.shutdown(1)
        request.close()

       
def join_chatroom(data):	
	chatroom_id=input_parser(data,"JOIN_CHATROOM:")
	client_name=input_parser(data,"CLIENT_NAME:") 
	chatroom_id = chatroom_id.strip(' \t\n\r')
	client_name = client_name.strip(' \t\n\r')
	chatroom_id=  sum([(ord(n)-ord('0')) * (10 ** i) for i,n in enumerate(reversed(chatroom_id))])
	#Add user to chatroom
	print client_name+ " joining chatroom..."+ str(chatroom_id)
	global mutex
	mutex.acquire()
	response_join(data)
	try:
		if chatroom_id in chatroom:
		    if client_name not in chatroom[chatroom_id]:
		        chatroom[chatroom_id].append(client_name)
		else:
		    chatroom[chatroom_id]=[client_name]
		    #multicast_chatroom(chatroom_id,"200\nClient already joined this chatroom.",client_name)
	finally:
			mutex.release()
	message=client_name +" has joined this chatroom."
	print message
	multicast_chatroom(chatroom_id,message,client_name)
	
		
def leave_chatroom(data):
	chatroom_id=input_parser(data,"LEAVE_CHATROOM:")
	chatroom_id = chatroom_id.strip(' \t\n\r')
	chatroom_id=int(chatroom_id);
#	chatroom_id.replace(" ", "")
	client_name=input_parser(data,"CLIENT_NAME:")
	client_name = client_name.strip(' \t\n\r')
	client_name.replace(" ", "")
	print client_name +" leaving chatroom..."+ str(chatroom_id);
	global mutex
	response_leave(data)
	mutex.acquire()
	try:
		if chatroom_id in chatroom:	
			if client_name in chatroom[chatroom_id]:
			    message=client_name+" has left this chatroom."
			    mutex.release()	
			    multicast_chatroom(chatroom_id,message,client_name)
			    mutex.acquire()
			    chatroom[chatroom_id].remove(client_name)	
		else:
			print "leaving through return";
			#return		
	finally: 
		mutex.release()	
#		print 2;
	
def multicast_chatroom(chatroom_id,message,client_name):
	print chatroom
	print "Mutlicasting to chatroom "+str(chatroom_id)+" Message: "+message+"\n"
	global mutex
	mutex.acquire()
	try:
		if chatroom_id in chatroom:
			print 1
			multicast_membership= chatroom[chatroom_id]
			print multicast_membership
    		for user in multicast_membership: 
    			   print 3
    			   CHAT= str(chatroom_id)
    			   CLIENT_NAME= client_name
    			   print "Sending to " +user
    			   to_send= "CHAT:"+str(CHAT)+"\nCLIENT_NAME:"+CLIENT_NAME+"\nMESSAGE:"+message+"\n\n"
    			   print to_send 
    			   client_connections[user].sendall(to_send)
    					
	finally:
	    print "ending"
	    mutex.release()
def send_message(data):
	CHAT= input_parser(data,"CHAT:")
	CLIENT_NAME= input_parser(data,"CLIENT_NAME:")
	MESSAGE= input_parser(data,"MESSAGE:")
	CLIENT_NAME = CLIENT_NAME.strip(' \t\n\r')
	CHAT = CHAT.strip(' \t\n\r')
	MESSAGE = MESSAGE.strip(' \t\n\r')
	#to_send=CHAT+"\n"+CLIENT_NAME+"\n"+MESSAGE
	chatroom_id=int(CHAT)
	multicast_chatroom(chatroom_id,MESSAGE,CLIENT_NAME)

def input_parser(data,command):
	index=data.find(command)
	output=(data[(index+len(command)):]).split('\n', 1)[0]
	return output

	
	
	
   
class TCPServerChange(SocketServer.TCPServer):
  def server_close(self):
       print"CLOSING SERVER"
  def close_request(self, request):
        print "Called to clean up an individual request."
  def shutdown_request(self, request):
        print "howya doing trying to close this socket are ya"
        print request


    
class ThreadedTCPServer(ThreadingPoolMixIn, TCPServerChange):
		pass

server = ThreadedTCPServer(('',int(sys.argv[1])), ThreadedTCPRequestHandler)
		
if __name__ == "__main__":
	server.serve_forever()
	


