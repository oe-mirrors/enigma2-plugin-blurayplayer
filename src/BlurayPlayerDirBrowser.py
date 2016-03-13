import os

from enigma import eTimer
from Components.ActionMap import ActionMap
from Components.config import config
from Components.Console import Console
from Components.FileList import FileList
from Components.Sources.StaticText import StaticText
from Screens.Screen import Screen
from Tools.BoundFunction import boundFunction

from . import _
from BlurayUi import BlurayMain


class BlurayPlayerDirBrowser(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		self.session = session
		self.skinName = ['BlurayPlayerDirBrowser', 'FileBrowser']
		self['key_red'] = StaticText(_('Exit'))
		self['key_green'] = StaticText(_('Ok'))
		self['filelist'] = FileList(directory = config.usage.default_path.value,
				matchingPattern = '(?i)^.*\.(iso)', enableWrapAround = True)
		self['FilelistActions'] = ActionMap(['SetupActions', 'ColorActions'],
				{
					'cancel': self.close,
					'red': self.close,
					'ok': self.ok,
					'green': self.ok
				})
		self.setTitle(_('Please select the blu-ray disc'))

	def ok(self):
		fileName = self['filelist'].getFilename()
		if fileName and fileName[-1:] == '/' and \
				os.path.isdir(os.path.join(fileName, 'BDMV/STREAM/')):
			self.session.open(BlurayMain, fileName)
		elif self['filelist'].canDescent():
			self['filelist'].descent()
		elif fileName and fileName[-1:] != '/':
			currentDir = self['filelist'].getCurrentDirectory()
			iso_path = os.path.join(currentDir, fileName).replace(' ', '\ ')
			mount_path = '/media/Bluray_%s' % \
					os.path.splitext(iso_path)[0].rsplit('/', 1)[1]
			if os.path.exists(mount_path):
				Console().ePopen('umount -f %s' % mount_path)
			else:
				try:
					os.mkdir(mount_path)
				except Exception as e:
					print '[BlurayPlayer] Cannot create', mount_path, e
			Console().ePopen('mount -r %s %s' % (iso_path, mount_path),
					self.mountIsoCallback, (mount_path, True))

	def mountIsoCallback(self, result, retval, extra_args):
		if not extra_args[1]:
			del self.remountTimer
		if os.path.isdir(os.path.join(extra_args[0], 'BDMV/STREAM/')):
			self.session.open(BlurayMain, extra_args[0])
		elif extra_args[1]:
			self.remountTimer = eTimer()
			self.remountTimer.timeout.callback.append(boundFunction(self.mountIsoCallback,
					None, None, (extra_args[0], False)))
			self.remountTimer.start(2000, False)
		else:
			Console().ePopen('umount -f %s' % extra_args[0],
					self.umountIsoCallback, extra_args[0])

	def umountIsoCallback(self, result, retval, extra_args):
		try:
			os.rmdir(extra_args)
		except Exception as e:
			print '[BlurayPlayer] Cannot remove', extra_args, e
