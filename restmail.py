#!/usr/bin/env python

from inbox import Inbox
import email.parser
import mimetypes
import time
import zlib
import copy

import hashlib

import asyncore
import socket

import json



class StorageHandler( object ):
	def __init__( self ):
		self.messages = {}
		self.attachments = {}
		self.inboxes = {}
	
	def store_mail( self, message ):
		recps = [ recp.lower() for recp in message['to'] ]
		
		message['id'] = hashlib.md5( recp + str( time.time() ) ).hexdigest()
		
		message['content'] = zlib.compress( message['content'], 9 )
		
		self.messages[ message['id'] ] = message
		
		for recp in recps:
			if recp not in self.inboxes:
				self.inboxes[recp] = []
		
			self.inboxes[recp].append( message['id'] )
	
	def store_attachment( self, payload, mimetype ):
		id = hashlib.sha1( payload ).hexdigest()
		self.attachments[ id ] = (zlib.compress( payload, 9 ), mimetype)
		return id
	
	def get_mail( self, recp, *args, **kwargs ):
		out = []
		if recp not in self.inboxes:
			return out
		
		for msg_id in self.inboxes[recp]:
			found = True
			msg2 = copy.deepcopy( self.messages[msg_id] )
			msg2['content'] = zlib.decompress( msg2['content'] )
				
			for (key, value) in kwargs.items():
				if value not in msg2[key]:
					found = False
			if found:
				out.append( msg2 )
		return out
	
	def get_attachment( self, id ):
		if id not in self.attachments:
			return ("", "text/plain" )
		else:
			return (zlib.decompress( self.attachments[id][0] ), self.attachments[id][1])
		

class HttpHandler( asyncore.dispatcher_with_send ):
	def __init__( self, sock, store ):
		asyncore.dispatcher_with_send.__init__(self, sock)
		self.store = store
		self.inbuffer = ""
		self.outbuffer = ""
		self.headers = {}
		self.headers_received = False
		self.body = ""
	
	def parse_headers( self, data ):
		lines = data.splitlines()
		(method, path, version) = lines[0].split()
		for line in lines:
			if ':' in line:
				(key, value) = line.split( ':', 1 )
				self.headers[key.strip().lower()] = value.strip()
		
		self.headers['http'] = (method, path, version )
		self.headers_received = True
		
	def generate_http_response( self, payload, mimetype ):
		out  = "HTTP/1.1 200 Ok.\r\n"
		out += "Content-Type: %s\r\n"%mimetype
		out += "Content-Length: %i\r\n"%( len( payload ) )
		out += "Connection: close\r\n"
		out += "\r\n"
		out += payload
		return out
	
	
	def handle_http_request( self ):
		#print "handle_http_request"
		(method, path, version ) = self.headers['http']
		content = ""
		mime = 'application/json'
		if method == "GET":
			parts = path.split( "/" )[1:]
			if parts[0] == "inbox":
				if len( parts ) > 1:					
					recp = parts[1]
					if '@' in recp:
						mails = self.store.get_mail( recp )
						content = json.dumps( mails, indent = 2 )
			if parts[0] == "files":
				if len( parts ) > 1:
					(content, mime ) = self.store.get_attachment( parts[1] )
		
		self.outbuffer += self.generate_http_response( content , mime )
					
		
		self.header_received = False
		self.headers = {}
		self.body = ""
	
	def writable(self):
		return len( self.outbuffer ) >= 0
	
	def handle_write(self):
		sent = self.send(self.outbuffer)
		self.outbuffer = self.outbuffer[:sent]
	
	def handle_close( self ):
		self.close()
		
	
	def handle_read( self ):
		chunk = self.recv( 8192 )
		if chunk:
			self.inbuffer += chunk
		
		if '\r\n\r\n' in self.inbuffer:
			(header, body) = self.inbuffer.split( '\r\n\r\n', 1 )
			self.parse_headers( header )
			self.body = body
			self.inbuffer = ""
		
		if self.headers_received:
			if 'http' in self.headers:
				if self.headers['http'][0] == "GET":
					self.handle_http_request()
				else:				
					self.body += self.inbuffer
					self.inbuffer = ""
					if len( self.body ) >= self.headers['content-length']:
						self.handle_http_request()

class HttpServer( asyncore.dispatcher ):
	def __init__( self, host, port, storage ):
		asyncore.dispatcher.__init__(self)
		self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
		self.set_reuse_addr()
		self.bind((host, port))
		self.listen(5)
		self.storage = storage
	
	def handle_accept(self):
		pair = self.accept()
		if pair is None:
			pass
		else:
			sock, addr = pair
			handler = HttpHandler( sock, self.storage )


inbox = Inbox()
storage = StorageHandler()

@inbox.collate
def handle( to, sender, body ):
	parser = email.parser.Parser()
	mail = parser.parsestr( body )
	message = {}
	message['to'] = to
	message['sender'] = unicode(sender)
	message['subject'] = mail['subject']
	message['received'] = time.strftime( "%Y-%m-%d %H:%M:%S" )
	message['content'] = ""
	message['attachments'] = []
	
	for part in mail.walk():
		if part.get_content_maintype() == "multipart":
			continue
		
		if not part.get_filename():
			if part.get_content_maintype() == "text":
				message['content'] += part.get_payload( decode = False )
		else:
			attachment = {}
			attachment['filename'] = part.get_filename()
			attachment['type'] = part.get_content_type()
			payload = part.get_payload( decode = True )
			attachment['payload-id'] = storage.store_attachment( payload, part.get_content_type() )
			message['attachments'].append( attachment)
			
	storage.store_mail( message )
			
			

server = HttpServer( '0.0.0.0', 8123, storage )

inbox.serve(address='0.0.0.0', port=4467)
