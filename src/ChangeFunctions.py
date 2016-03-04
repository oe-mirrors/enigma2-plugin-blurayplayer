import os
from types import MethodType

from Components.Console import Console
from Screens.MovieSelection import MovieSelection


# Replaces the original gotFilename to add bluray folder test at the beginning
# If test fails call original gotFilename as orig_gotFilename to to keep the code unchanged
old_gotFilename = MovieSelection.gotFilename


def gotFilename(self, res, selItem=None):
	if res and os.path.isdir(res):
		folder = os.path.join(res, 'STREAM/')
		if 'BDMV/STREAM/' not in folder:
			folder = folder[:-7] + 'BDMV/STREAM/'
		if os.path.isdir(folder):
			try:
				from Plugins.Extensions.BlurayPlayer import BlurayUi
				self.session.open(BlurayUi.BlurayMain, res)
			except Exception as e:
				print '[BlurayPlayer] Cannot open BlurayPlayer:', e
			else:
				return
	self.orig_gotFilename(res, selItem)


MovieSelection.orig_gotFilename = MethodType(old_gotFilename, None, MovieSelection)
MovieSelection.gotFilename = gotFilename


# Replaces the original itemSelectedCheckTimeshiftCallback to add iso mount at the beginning
# If mount fails call original as orig_itemSelectedCheckTimeshiftCallback to to keep code unchanged
old_Callback = MovieSelection.itemSelectedCheckTimeshiftCallback


def itemSelectedCheckTimeshiftCallback(self, ext, path, answer):
	if answer:
		if ext == '.iso' and path[:10] != '/media/net':
			if os.path.exists('/media/Bluray'):
				Console().ePopen('umount -f /media/Bluray')
			else:
				try:
					os.mkdir('/media/Bluray')
				except Exception as e:
					print '[BlurayPlayer] Cannot create /media/Bluray', e
			path = path.replace(' ', '\ ')
			Console().ePopen('mount -r %s /media/Bluray' % path, self.mountIsoCallback, path)
		else:
			self.orig_itemSelectedCheckTimeshiftCallback(ext, path, answer)


def mountIsoCallback(self, result, retval, extra_args):
	if os.path.isdir('/media/Bluray/BDMV/STREAM'):
		self.gotFilename('/media/Bluray')
	else:
		Console().ePopen('umount -f /media/Bluray')
		try:
			os.rmdir('/media/Bluray')
		except Exception as e:
			print '[BlurayPlayer] Cannot remove /media/Bluray', e
		self.orig_itemSelectedCheckTimeshiftCallback(ext='.iso', path=extra_args, answer=True)


MovieSelection.orig_itemSelectedCheckTimeshiftCallback = MethodType(old_Callback, None, MovieSelection)
MovieSelection.mountIsoCallback = MethodType(mountIsoCallback, None, MovieSelection)
MovieSelection.itemSelectedCheckTimeshiftCallback = itemSelectedCheckTimeshiftCallback
