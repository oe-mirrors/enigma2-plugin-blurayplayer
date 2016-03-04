import os

from enigma import ePicLoad, eServiceReference
from Components.ActionMap import ActionMap
from Components.AVSwitch import AVSwitch
from Components.Console import Console
from Components.Label import Label
from Components.Pixmap import Pixmap
from Components.Sources.List import List
from Components.Sources.StaticText import StaticText
from Screens.InfoBar import InfoBar, MoviePlayer
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from Tools.Directories import resolveFilename, SCOPE_PLUGINS

from . import _
import blurayinfo


class BlurayPlayer(MoviePlayer):
	def __init__(self, session, service):
		MoviePlayer.__init__(self, session, service)
		self.skinName = 'MoviePlayer'
		self.servicelist = InfoBar.instance and InfoBar.instance.servicelist

	def handleLeave(self, how):
		if how == 'ask':
			self.session.openWithCallback(self.leavePlayerConfirmed,
				MessageBox, _('Stop playing this movie?'))
		else:
			self.close()

	def leavePlayerConfirmed(self, answer):
		if answer:
			self.close()

	def showMovies(self):
		pass


class BlurayMain(Screen):
	skin = """
		<screen position="center,center" size="630,300">
			<widget name="name" position="10,10" size="620,60" halign="center" font="Regular;30" />
			<widget source="list" render="Listbox" position="10,70" size="300,170" \
				scrollbarMode="showOnDemand" >
				<convert type="TemplatedMultiContent" >
				{
					"template": [MultiContentEntryText(pos=(10, 1), size=(600, 30), \
							font=0, flags=RT_HALIGN_LEFT|RT_VALIGN_CENTER, text=0)],
					"fonts": [gFont("Regular", 20)],
					"itemHeight": 30
				}
				</convert>
			</widget>
			<widget name="thumbnail" position="320,70" size="300,170" transparent="1" alphatest="on" />
			<ePixmap position="114,251" size="140,40" pixmap="skin_default/buttons/red.png" \
				transparent="1" alphatest="on" />
			<ePixmap position="378,251" size="140,40" pixmap="skin_default/buttons/green.png" \
				transparent="1" alphatest="on" />
			<widget source="key_red" render="Label" position="110,258" zPosition="2" size="148,30" \
				valign="center" halign="center" font="Regular;22" transparent="1" />
			<widget source="key_green" render="Label" position="370,258" zPosition="2" size="148,30" \
				valign="center" halign="center" font="Regular;22" transparent="1" />
		</screen>"""

	def __init__(self, session, res):
		Screen.__init__(self, session)
		self.setTitle(_('Blu-ray player'))
		self.session = session
		self.res = res
		self.name = ''
		self['key_red'] = StaticText(_('Exit'))
		self['key_green'] = StaticText(_('Ok'))
		self['actions'] = ActionMap(['OkCancelActions', 'ColorActions'],
			{
				'cancel': self.close,
				'red': self.close,
				'ok': self.Ok,
				'green': self.Ok,
			})
		self['list'] = List([])
		self['name'] = Label()
		self['thumbnail'] = Pixmap()

		content = []
		x = 1
		try:
			for title in blurayinfo.getTitles(self.res):
				playfile = os.path.join(self.res, 'BDMV/STREAM/', title[1] + '.m2ts')
				title_entry = _('%d. Duration %d:%02d minutes') % \
						(x, title[0] / (45000 * 60), (title[0] / 45000) % 60)
				content.append((title_entry, playfile))
				x += 1
		except Exception as e:
			print '[BlurayPlayer] blurayinfo.getTitles:', e
			content.append((_('Error in reading tiles!'), None))
		self['list'].setList(content)
		self.onLayoutFinish.append(self.LayoutFinish)

	def LayoutFinish(self):
		thumbnail = None
		path = os.path.join(self.res, 'BDMV/META/DL/')
		if os.path.exists(path):
			fileSize = 1000000
			for x in os.listdir(path):
				dlFile = os.path.join(path, x)
				if dlFile[-4:] == '.xml':
					try:
						self.name = open(dlFile).read()\
								.split('<di:name>')[1].split('</di:name>')[0]
					except:
						pass
				elif dlFile[-4:] == '.jpg':
					size = os.stat(dlFile).st_size
					if size > 0 and size < fileSize:
						fileSize = size
						thumbnail = dlFile

		if not self.name:
			if self.res[-1:] == '/':
				self.res = self.res[:-1]
			try:
				self.name = self.res.rsplit('/', 1)[1]
			except:
				self.name = 'Bluray'
		self['name'].setText(self.name)

		if not thumbnail:
			thumbnail = resolveFilename(SCOPE_PLUGINS,
					'Extensions/BlurayPlayer/icon.png')
		size = AVSwitch().getFramebufferScale()
		self.picloads = ePicLoad()
		self.picloads.PictureData.get().append(self.FinishDecode)
		self.picloads.setPara((
				self['thumbnail'].instance.size().width(),
				self['thumbnail'].instance.size().height(),
				size[0], size[1], False, 1, '#00000000'))
		self.picloads.startDecode(thumbnail)

	def FinishDecode(self, picInfo = None):
		ptr = self.picloads.getData()
		if ptr:
			self['thumbnail'].instance.setPixmap(ptr.__deref__())
			del self.picloads

	def Ok(self):
		current = self['list'].getCurrent()
		if current and current[1]:
			ref = eServiceReference(3, 0, current[1])
			ref.setName(self.name)
			self.session.openWithCallback(self.MoviePlayerCallback, BlurayPlayer, ref)

	def MoviePlayerCallback(self):
		if self.res == '/media/bluray':
			Console().ePopen('umount -f /media/bluray', self.umountIsoCallback)
		else:
			self.close()

	def umountIsoCallback(self, result, retval, extra_args):
		try:
			os.rmdir('/media/bluray')
		except Exception as e:
			print '[BlurayPlayer] remove directory /media/bluray:', e
		self.close()
