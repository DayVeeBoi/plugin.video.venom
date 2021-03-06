# -*- coding: utf-8 -*-
'''
	Venom Add-on
'''

from datetime import datetime
import inspect
import xbmc

# only prints if venom set to "Debug"
LOGDEBUG = 0
LOGINFO = 1
###--from here down methods print when "Normal" venom setting.
LOGNOTICE = 2 #deprecated in 19(use LOGINFO) chk if #'s change in 19
LOGWARNING = 3
LOGERROR = 4
LOGSEVERE = 5 #deprecated in 19(use LOGFATAL)
LOGFATAL = 6
LOGNONE = 7

from resources.lib.modules import control

DEBUGPREFIX = '[COLOR red][ Venom DEBUG ][/COLOR]'
LOGPATH = control.transPath('special://logpath/')


def log(msg, caller=None, level=LOGNOTICE):
	debug_enabled = control.setting('debug.enabled') == 'true'
	if not debug_enabled: return
	debug_level = control.setting('debug.level')
	if level == LOGDEBUG and debug_level != '1': return
	debug_location = control.setting('debug.location')
	try:
		if caller is not None and level == LOGDEBUG:
			func = inspect.currentframe().f_back.f_code
			line_number = inspect.currentframe().f_back.f_lineno
			caller = "%s.%s()" % (caller, func.co_name)
			msg = 'From func name: %s Line # :%s\n                       msg : %s' % (caller, line_number, msg)
		if caller is not None and level == LOGERROR:
			msg = 'From func name: %s.%s() Line # :%s\n                       msg : %s' % (caller[0], caller[1], caller[2], msg)
		try:
			if isinstance(msg, unicode):
				msg = '%s (ENCODED)' % (msg.encode('utf-8'))
		except: pass
		if debug_location == '1':
			log_file = control.joinPath(LOGPATH, 'venom.log')
			if not control.existsPath(log_file):
				f = open(log_file, 'w')
				f.close()
			with open(log_file, 'a') as f:
				line = '[%s %s] %s: %s' % (datetime.now().date(), str(datetime.now().time())[:8], DEBUGPREFIX, msg)
				f.write(line.rstrip('\r\n')+'\n')
		else:
			xbmc.log('%s: %s' % (DEBUGPREFIX, msg), level)
	except Exception as e:
		xbmc.log('Logging Failure: %s' % (e), LOGERROR)


def error(message=None, exception=True):
	try:
		import sys
		if exception:
			type, value, traceback = sys.exc_info()
			addon = 'plugin.video.venom'
			filename = (traceback.tb_frame.f_code.co_filename)
			filename = filename.split(addon)[1]
			name = traceback.tb_frame.f_code.co_name
			linenumber = traceback.tb_lineno
			errortype = type.__name__
			errormessage = value.message or value # sometimes value.message is null while value is not
			if str(errormessage) == '': return
			if message: message += ' -> '
			else: message = ''
			message += str(errortype) + ' -> ' + str(errormessage)
			caller = [filename, name, linenumber]
		else:
			caller = None
		log(msg=message, caller=caller, level=LOGERROR)
		del(type, value, traceback) # So we don't leave our local labels/objects dangling
	except Exception as e:
		xbmc.log('Logging Failure: %s' % (e), LOGERROR)


class Profiler(object):
	import cProfile
	import pstats
	import time
	from json import dumps as jsdumps, loads as jsloads
	try: from StringIO import StringIO
	except ImportError: from io import StringIO


	def __init__(self, file_path, sort_by='time', builtins=False):
		self._profiler = cProfile.Profile(builtins=builtins)
		self.file_path = file_path
		self.sort_by = sort_by


	def profile(self, f):
		def method_profile_on(*args, **kwargs):
			try:
				self._profiler.enable()
				result = self._profiler.runcall(f, *args, **kwargs)
				self._profiler.disable()
				return result
			except Exception as e:
				log('Profiler Error: %s' % (e), LOGWARNING)
				return f(*args, **kwargs)


		def method_profile_off(*args, **kwargs):
			return f(*args, **kwargs)
		if _is_debugging(): return method_profile_on
		else: return method_profile_off


	def __del__(self):
		self.dump_stats()


	def dump_stats(self):
		if self._profiler:
			s = StringIO()
			params = (self.sort_by,) if isinstance(self.sort_by, basestring) else self.sort_by
			ps = pstats.Stats(self._profiler, stream=s).sort_stats(*params)
			ps.print_stats()
			if self.file_path:
				with open(self.file_path, 'w') as f:
					f.write(s.getvalue())


def trace(method):
	def method_trace_on(*args, **kwargs):
		start = time.time()
		result = method(*args, **kwargs)
		end = time.time()
		log('{name!r} time: {time:2.4f}s args: |{args!r}| kwargs: |{kwargs!r}|'.format(name=method.__name__, time=end - start, args=args, kwargs=kwargs), LOGDEBUG)
		return result

	def method_trace_off(*args, **kwargs):
		return method(*args, **kwargs)
	if _is_debugging(): return method_trace_on
	else: return method_trace_off


def _is_debugging():
	command = {'jsonrpc': '2.0', 'id': 1, 'method': 'Settings.getSettings', 'params': {'filter': {'section': 'system', 'category': 'logging'}}}
	js_data = execute_jsonrpc(command)
	for item in js_data.get('result', {}).get('settings', {}):
		if item['id'] == 'debug.showloginfo':
			return item['value']
	return False


def execute_jsonrpc(command):
	if not isinstance(command, basestring):
		command = jsdumps(command)
	response = control.jsonrpc(command)
	return jsloads(response)