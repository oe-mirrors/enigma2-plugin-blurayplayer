import os

from Components.ActionMap import ActionMap
from Components.config import config
from Components.Console import Console
from Components.FileList import FileList
from Components.Sources.StaticText import StaticText
from Screens.Screen import Screen

from . import _
from BlurayUi import BlurayMain


class BlurayPlayerDirBrowser(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		self.session = session
		self.skinName = ['BlurayPlayerDirBrowser', 'FileBrowser']
		self['key_red'] = StaticText(_('Exit'))
		self['key_green'] = StaticText(_('Ok'))
		filelist = FileList(directory = config.usage.default_path.value,
				matchingPattern = '(?i)^.*\.(iso)')
		self['filelist'] = filelist
		self['FilelistActions'] = ActionMap(['SetupActions', 'ColorActions'],
				{
					'cancel': self.close,
					'red': self.close,
					'ok': self.ok,
					'green': self.ok
				})
		self.onLayoutFinish.append(self.layoutFinished)

	def layoutFinished(self):
		self.setTitle(_('Please select the blu-ray disc'))

	def ok(self):
		fileName = self['filelist'].getFilename()
		if fileName[-1:] == '/' and \
				os.path.isdir(os.path.join(fileName, 'BDMV/STREAM/')):
			self.session.open(BlurayMain, fileName)
		elif self['filelist'].canDescent():
			self['filelist'].descent()
		elif fileName[-1:] != '/':
			currentDir = self['filelist'].getCurrentDirectory()
			iso_path = os.path.join(currentDir, fileName).replace(' ', '\ ')
			mount_path = '/media/Bluray_' + \
					iso_path.rsplit('/', 1)[1].replace('.iso', '')
			if os.path.exists(mount_path):
				Console().ePopen('umount -f %s' % mount_path)
			else:
				try:
					os.mkdir(mount_path)
				except Exception as e:
					print '[BlurayPlayer] Cannot create', mount_path, e
			Console().ePopen('mount -r %s %s' % (iso_path, mount_path),
					self.mountIsoCallback, mount_path)

	def mountIsoCallback(self, result, retval, extra_args):
		if os.path.isdir(os.path.join(extra_args, 'BDMV/STREAM/')):
			self.session.open(BlurayMain, extra_args)
		else:
			Console().ePopen('umount -f %s' % extra_args, self.umountIsoCallback, extra_args)

	def umountIsoCallback(self, result, retval, extra_args):
		try:
			os.rmdir(extra_args)
		except Exception as e:
			print '[BlurayPlayer] Cannot remove', extra_args, e
