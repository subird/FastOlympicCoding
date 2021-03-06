#!/usr/bin/python
import sys

sys.path.append('/Applications/Xcode.app/Contents/SharedFrameworks/LLDB.framework/Resources/Python')

import lldb
import os
from time import time
import subprocess
from os import path
import threading


def wait(ms):
	print 'wait: ' + str(ms)
	start = time()
	while abs(start - time()) < ms:
		pass
	print 'wait: continue'


def disassemble_instructions(insts):
	for i in insts:
		print 'dis', i

def encode(s):
	return str([ord(c) for c in s])
	return s

def decode(data):
	s = ''
	# print("data:", data)
	if not data:
		return ''
	data = eval(data.rstrip())
	for x in data:
		s += chr(x)
	return s
		

class Debugger(object):
	"""docstring for Debugger"""

	COMPILE_CMD = 'g++ -std=gnu++11 -g -o main "{name}"'


	def __init__(self, file):
		super(Debugger, self).__init__()
		self.file = file
		self.process = None
		self.main_thread = None
		self.sbdbg = None
		self.state = 'WAITING'
		self.debugger = None

	def change_state(self, new_state):
		self.state = new_state

	def clear(self):
		debugger = self.sbdbg
		if debugger:
			self.add_buff()
			self.process.Kill()
			lldb.SBDebugger.Destroy(self.sbdbg)
		
	def compile(self):
		PIPE = subprocess.PIPE
		p = subprocess.Popen(self.COMPILE_CMD.format(name=self.file), \
			shell=True, stdin=PIPE, stdout=PIPE, stderr=subprocess.STDOUT, \
				cwd=os.path.split(self.file)[0])
		self.change_state('COMPILING')
		p.wait()
		return (p.returncode, p.stdout.read().decode())

	def filter_frames(self):
		main_thread = self.main_thread
		frames = main_thread.frames
		cur_frames = []
		# print(self.file)
		for frame in frames:
			# print '!', type(frame.line_entry.file), '!'
			if frame.line_entry.file.__str__() == self.file:
				# print(frame.line_entry.file)
				cur_frames.append(frame)
		self.stack_frames = cur_frames

	def get_crash_frame(self):
		for frame in self.main_thread.frames:
			if frame.line_entry.file.__str__() == self.file:
				return frame

	class ExitListener(threading.Thread):
		def run(self):
			_ = self._dbg
			process = _.process
			broadcaster = process.GetBroadcaster()
			event = lldb.SBEvent()
			listener = lldb.SBListener('ExitListener')
			rc = broadcaster.AddListener(listener, lldb.SBProcess.eBroadcastBitStateChanged)
			while True:
				if listener.WaitForEventForBroadcasterWithType(lldb.eStateExited,
															   broadcaster,
															   lldb.SBProcess.eBroadcastBitStateChanged,
															   event):
					# print _.sbdbg.StateAsCString(process.GetState())
					if process.GetState() == lldb.eStateExited:
						_.state = 'EXITED'
						_.rtcode = process.GetExitStatus()
						_.clear()
						break
					elif process.GetState() == lldb.eStateStopped:
						_.filter_frames()
						frame = _.get_crash_frame()
						_.crash_line = int(frame.line_entry.GetLine().__str__())
						_.rtcode = process.GetExitStatus()
						# print(frame.line_entry.GetLine())
						_.state = 'STOPPED'
						# _.filter_frames()
						break

				else:
					'OK lets try again'
					pass # dont forget

	def run(self):
		self.buff = ''
		exe = path.join(path.dirname(self.file), 'main')

		self.clear()
		dbg = lldb.SBDebugger.Create()
		dbg.SetAsync(True)
		target = dbg.CreateTargetWithFileAndArch(exe, lldb.LLDB_ARCH_DEFAULT)
		self.miss_cnt = 0
		process = target.LaunchSimple(None, None, path.dirname(self.file))
		self.change_state('RUNNING')
		# print(self.is_stopped())
		# print('__runed')
		self.process = process
		self.main_thread = self.process.GetThreadAtIndex(0)
		self.sbdbg = dbg

		exit_listener = self.ExitListener()
		exit_listener._dbg = self
		exit_listener.start()
		self.exit_listener = exit_listener

		# print(dir(dbg))
		# print(dir(target))
		# print(dir(process))

	def add_buff(self):
		out = self.process.GetSTDOUT(2 ** 18)
		if out:
			# print(out.encode(), out[5:].encode())
			out = out.__str__()
			out = out.replace('\r\n', '\n')
			miss = min(self.miss_cnt, len(out))
			# print(miss)
			out = out[miss:]
			# print(':', out)
			self.miss_cnt -= miss
			self.buff += out

	def destroy(self):
		self.process.Kill()
		lldb.SBDebugger.Destroy(self.sbdbg)

	def terminate(self):
		self.process.Kill()

	def put_stdin(self, s):
		self.add_buff()
		self.process.PutSTDIN(s)
		# print('LENNN', len(s))
		self.miss_cnt += len(s)

	def get_output(self):
		self.add_buff()
		s = self.buff
		self.buff = ''
		return s
		
	def get_var_value(self, var_name, frame_id=None):
		if frame_id is None:
			frame = self.get_crash_frame()
		else:
			frame = self.main_thread.GetFrameAtIndex(frame_id)
		return frame.FindVariable(var_name)


# file = '/Users/Uhuhu/Desktop/temp/_temp2/main.cpp'


file = '/Users/Uhuhu/Library/Application Support/Sublime Text 3/Packages/FastOlympicCoding/debuggers/main.cpp'

if len(sys.argv) > 1:
	file = sys.argv[1]
debugger = Debugger(file)


# print(debugger.compile())
def _console_connecter(debugger):
	global decode
	global encode
	_ = debugger
	def quit():
		debugger.destroy()
		exit(0)

	def do_run():
		_.compile()
		_.run()

	def test(frame_id):
		thread = debugger.process.GetThreadAtIndex(0)
		frame = thread.GetFrameAtIndex(frame_id)
		print frame
		print frame.arguments
		print frame.get_all_variables()
		print "find results"
		print frame.FindVariable('v')


	while True:

		print(encode(input().__str__()))
		# print('____')
		sys.stdout.flush()
		# query = raw_input().rstrip()
		# if query == 'compile':
		# 	debugger.compile()
		# elif query == 'run':
		# 	debugger.run()
		# elif query == 'is_running':
		# 	print(debugger.is_running())
		# elif query == 'destroy':
		# 	debugger.destroy()
		# elif query == 'get_state':
		# 	print(debugger.state())
		# elif query == 'put_stdin':
		# 	debugger.put_stdin()
		# elif query == 'get_output':
		# 	print(debugger.get_output())
		# elif query == 'exit':
		# 	debugger.destroy()
		# 	exit(0)

_console_connecter(debugger)
		

exit(0)
debugger.compile()
debugger.run()
debugger.destroy()




# Set the path to the executable to debug
exe = "./a.out"

# Create a new debugger instance
debugger = lldb.SBDebugger.Create()

# When we step or continue, don't return from the function until the process 
# stops. Otherwise we would have to handle the process events ourselves which, while doable is
#a little tricky.  We do this by setting the async mode to false.
debugger.SetAsync (False)

# Create a target from a file and arch
print "Creating a target for '%s'" % exe

target = debugger.CreateTargetWithFileAndArch (exe, lldb.LLDB_ARCH_DEFAULT)

if target:
	# If the target is valid set a breakpoint at main
	main_bp = target.BreakpointCreateByName ("i_am_void", target.GetExecutable().GetFilename());

	print main_bp

	# Launch the process. Since we specified synchronous mode, we won't return
	# from this function until we hit the breakpoint at main
	process = target.LaunchSimple (None, None, os.getcwd())
	
	# Make sure the launch went ok
	if process:
		wait(2)
		print 'out - ', process.GetSTDOUT(1024)
		# Print some simple process info
		state = process.GetState ()
		print process
		if state == lldb.eStateStopped:
			# Get the first thread
			thread = process.GetThreadAtIndex (0)
			if thread:
				# Print some simple thread info
				print thread
				# Get the first frame
				frame = thread.GetFrameAtIndex (4)
				if frame:
					# Print some simple frame info
					print frame
					print frame.arguments
					print frame.get_all_variables()
					print "find results"
					print frame.FindVariable('_pre')
					function = frame.GetFunction()
					# See if we have debug info (a function)
					if function:
						# We do have a function, print some info for the function
						print function
						# Now get all instructions for this function and print them
						insts = function.GetInstructions(target)
						disassemble_instructions (insts)
					else:
						# See if we have a symbol in the symbol table for where we stopped
						symbol = frame.GetSymbol();
						if symbol:
							# We do have a symbol, print some info for the symbol
							print symbol