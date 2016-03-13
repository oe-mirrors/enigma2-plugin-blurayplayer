import os

from enigma import eTimer
from Components.Console import Console
from Screens.MovieSelection import MovieSelection
from Tools.BoundFunction import boundFunction


isMovieSelection = True
try:
	old_gotFilename = MovieSelection.gotFilename
	old_Callback = MovieSelection.itemSelectedCheckTimeshiftCallback
except:
	isMovieSelection = False
	print '[BlurayPlayer] Plugin can not be used in MovieSelection'


# Replaces the original gotFilename to add bluray folder test at the beginning
# If test fails call original gotFilename as orig_gotFilename to to keep the code unchanged
def gotFilename(self, res, selItem=None):
	if res and os.path.isdir(res):
		if os.path.isdir(os.path.join(res, 'BDMV/STREAM/')):
			try:
				from Plugins.Extensions.BlurayPlayer import BlurayUi
				self.session.open(BlurayUi.BlurayMain, res)
			except Exception as e:
				print '[BlurayPlayer] Cannot open BlurayPlayer:', e
			else:
				return
	self.orig_gotFilename(res, selItem)


# Replaces the original itemSelectedCheckTimeshiftCallback to add iso mount at the beginning
# If mount fails call original as orig_itemSelectedCheckTimeshiftCallback to to keep code unchanged
def itemSelectedCheckTimeshiftCallback(self, ext, path, answer):
	if answer:
		if ext == '.iso':
			iso_path = path.replace(' ', '\ ')
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
					self.mountIsoCallback, (path, mount_path, 0))
		else:
			self.orig_itemSelectedCheckTimeshiftCallback(ext, path, answer)


def mountIsoCallback(self, result, retval, extra_args):
	path = extra_args[0]
	mount_path = extra_args[1]
	remount = extra_args[2]
	if remount != 0:
		del self.remountTimer
	if os.path.isdir(os.path.join(mount_path, 'BDMV/STREAM')):
		self.gotFilename(mount_path)
	elif remount < 5:
		remount += 1
		self.remountTimer = eTimer()
		self.remountTimer.timeout.callback.append(boundFunction(self.mountIsoCallback,
				None, None, (path, mount_path, remount)))
		self.remountTimer.start(2000, False)
	else:
		Console().ePopen('umount -f %s' % mount_path, self.umountIsoCallback, (path, mount_path))


def umountIsoCallback(self, result, retval, extra_args):
	try:
		os.rmdir(extra_args[1])
	except Exception as e:
		print '[BlurayPlayer] Cannot remove', extra_args[1], e
	self.orig_itemSelectedCheckTimeshiftCallback(ext='.iso', path=extra_args[0], answer=True)


if isMovieSelection:
	from types import MethodType

	MovieSelection.orig_gotFilename = MethodType(old_gotFilename, None, MovieSelection)
	MovieSelection.gotFilename = gotFilename
	MovieSelection.orig_itemSelectedCheckTimeshiftCallback = MethodType(old_Callback, None, MovieSelection)
	MovieSelection.mountIsoCallback = MethodType(mountIsoCallback, None, MovieSelection)
	MovieSelection.umountIsoCallback = MethodType(umountIsoCallback, None, MovieSelection)
	MovieSelection.itemSelectedCheckTimeshiftCallback = itemSelectedCheckTimeshiftCallback
