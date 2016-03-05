import os
from types import MethodType

from Components.Console import Console
from Screens.MovieSelection import MovieSelection


# Replaces the original gotFilename to add bluray folder test at the beginning
# If test fails call original gotFilename as orig_gotFilename to to keep the code unchanged
old_gotFilename = MovieSelection.gotFilename


def gotFilename(self, res, selItem=None):
	if res and os.path.isdir(res):
		folder = os.path.join(res, 'BDMV/STREAM/')
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
			iso_path = path.replace(' ', '\ ')
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
					self.mountIsoCallback, (path, mount_path))
		else:
			self.orig_itemSelectedCheckTimeshiftCallback(ext, path, answer)


def mountIsoCallback(self, result, retval, extra_args):
	path = extra_args[0]
	mount_path = extra_args[1]
	if os.path.isdir(os.path.join(mount_path, 'BDMV/STREAM')):
		self.gotFilename(mount_path)
	else:
		Console().ePopen('umount -f %s' % mount_path, self.umountIsoCallback, (path, mount_path))


def umountIsoCallback(self, result, retval, extra_args):
	try:
		os.rmdir(extra_args[1])
	except Exception as e:
		print '[BlurayPlayer] Cannot remove', extra_args[1], e
	self.orig_itemSelectedCheckTimeshiftCallback(ext='.iso', path=extra_args[0], answer=True)


MovieSelection.orig_itemSelectedCheckTimeshiftCallback = MethodType(old_Callback, None, MovieSelection)
MovieSelection.mountIsoCallback = MethodType(mountIsoCallback, None, MovieSelection)
MovieSelection.umountIsoCallback = MethodType(umountIsoCallback, None, MovieSelection)
MovieSelection.itemSelectedCheckTimeshiftCallback = itemSelectedCheckTimeshiftCallback
