import os

from enigma import ePicLoad, eServiceReference, eTimer, getDesktop
from Components.ActionMap import ActionMap
from Components.AVSwitch import AVSwitch
from Components.config import config, getConfigListEntry, \
	ConfigNothing, ConfigSelection, ConfigOnOff
from Components.Console import Console
from Components.Label import Label
from Components.Pixmap import Pixmap
from Components.Sources.List import List
from Components.Sources.StaticText import StaticText
from Screens.AudioSelection import AudioSelection
from Screens.InfoBar import InfoBar, MoviePlayer
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from Tools.Directories import resolveFilename, SCOPE_PLUGINS

from . import _
import blurayinfo


class BlurayAudioSelection(AudioSelection):
	def __init__(self, session, infobar, page, languages, codecs):
		AudioSelection.__init__(self, session, infobar, page)
		self.skinName = 'AudioSelection'
		self.languages = languages
		self.codecs = codecs

	def fillList(self, arg=None):
		from Components.SystemInfo import SystemInfo
		from Tools.ISO639 import LanguageCodes

		streams = []
		conflist = []
		selectedidx = 0

		self['key_blue'].setBoolean(False)

		if self.settings.menupage.getValue() == 'audio':
			self.setTitle(_('Select audio track'))
			service = self.session.nav.getCurrentService()
			self.audioTracks = audio = service and service.audioTracks()
			n = audio and audio.getNumberOfTracks() or 0
			if SystemInfo['CanDownmixAC3']:
				self.settings.downmix = ConfigOnOff(default=config.av.downmix_ac3.value)
				self.settings.downmix.addNotifier(self.changeAC3Downmix,
						initial_call=False)
				conflist.append(getConfigListEntry(_('Multi channel downmix'),
						self.settings.downmix))
				self['key_red'].setBoolean(True)

			if n > 0:
				self.audioChannel = service.audioChannel()
				if self.audioChannel:
					choicelist = [('0', _('left')), ('1', _('stereo')), ('2', _('right'))]
					self.settings.channelmode = ConfigSelection(choices=choicelist,
							default=str(self.audioChannel.getCurrentChannel()))
					self.settings.channelmode.addNotifier(self.changeMode, initial_call=False)
					conflist.append(getConfigListEntry(_('Channel'), self.settings.channelmode))
					self['key_green'].setBoolean(True)
				else:
					conflist.append(('',))
					self['key_green'].setBoolean(False)
				selectedAudio = self.audioTracks.getCurrentTrack()
				li = 0
				self.codecs.append('END')
				for x in range(n):
					number = str(x + 1)
					i = audio.getTrackInfo(x)
					languages = i.getLanguage().split('/')
					description = i.getDescription() or ''
					selected = ''
					language = ''

					if not languages[0] and description:
						while self.codecs[li] != description and self.codecs[li] != 'END':
							li += 1
						if self.codecs[li] == 'END':
							li = 0
						else:
							languages[0] = self.languages[li]
							li += 1

					if selectedAudio == x:
						selected = 'X'
						selectedidx = x

					cnt = 0
					for lang in languages:
						if cnt:
							language += ' / '
						if lang in LanguageCodes:
							language += _(LanguageCodes[lang][0])
						elif lang == 'und':
							''
						else:
							language += lang
						cnt += 1

					streams.append((x, '', number, description, language, selected))

			else:
				streams = []
				conflist.append(('',))
				self['key_green'].setBoolean(False)

			self['key_yellow'].setBoolean(False)
			conflist.append(('',))

			from Components.PluginComponent import plugins
			from Plugins.Plugin import PluginDescriptor

			if hasattr(self.infobar, 'runPlugin'):
				class PluginCaller:
					def __init__(self, fnc, *args):
						self.fnc = fnc
						self.args = args

					def __call__(self, *args, **kwargs):
						self.fnc(*self.args)

				self.Plugins = [(p.name, PluginCaller(self.infobar.runPlugin, p))
						for p in plugins.getPlugins(where=PluginDescriptor.WHERE_AUDIOMENU)]

				if self.Plugins:
					self['key_blue'].setBoolean(True)
					if len(self.Plugins) > 1:
						conflist.append(getConfigListEntry(_('Audio plugins'), ConfigNothing()))
						self.plugincallfunc = [(x[0], x[1]) for x in self.Plugins]
					else:
						conflist.append(getConfigListEntry(self.Plugins[0][0], ConfigNothing()))
						self.plugincallfunc = self.Plugins[0][1]

		self['config'].list = conflist
		self['config'].l.setList(conflist)

		self['streams'].list = streams
		self['streams'].setIndex(selectedidx)


class BlurayPlayer(MoviePlayer):
	def __init__(self, session, service, languages, codecs):
		MoviePlayer.__init__(self, session, service)
		self.skinName = 'MoviePlayer'
		self.servicelist = InfoBar.instance and InfoBar.instance.servicelist
		self.languages = languages
		self.codecs = codecs

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

	def audioSelection(self):
		self.session.open(BlurayAudioSelection, infobar=self, page='audio',
				languages=self.languages, codecs=self.codecs)


class BlurayMain(Screen):
	screenWidth = getDesktop(0).size().width()
	if screenWidth and screenWidth > 1280:
		skin = """
			<screen position="center,center" size="855,450">
				<widget name="name" position="15,15" size="825,90" halign="center" font="Regular;45" />
				<widget source="list" render="Listbox" position="15,105" size="510,255" \
					scrollbarMode="showOnDemand" >
					<convert type="TemplatedMultiContent" >
					{
						"template": [MultiContentEntryText(pos=(15, 1), size=(510, 45), \
								font=0, flags=RT_HALIGN_LEFT|RT_VALIGN_CENTER, text=0)],
						"fonts": [gFont("Regular", 30)],
						"itemHeight": 45
					}
					</convert>
				</widget>
				<widget name="thumbnail" position="540,105" size="300,170" transparent="1" alphatest="on" />
				<ePixmap position="126,376" size="210,60" pixmap="skin_default/buttons/red.png" \
					transparent="1" alphatest="on" />
				<ePixmap position="522,376" size="210,60" pixmap="skin_default/buttons/green.png" \
					transparent="1" alphatest="on" />
				<widget source="key_red" render="Label" position="120,387" zPosition="2" size="222,45" \
					valign="center" halign="center" font="Regular;33" transparent="1" />
				<widget source="key_green" render="Label" position="510,387" zPosition="2" size="222,45" \
					valign="center" halign="center" font="Regular;33" transparent="1" />
			</screen>"""
	else:
		skin = """
			<screen position="center,center" size="670,300">
				<widget name="name" position="10,10" size="650,60" halign="center" font="Regular;30" />
				<widget source="list" render="Listbox" position="10,70" size="340,170" \
					scrollbarMode="showOnDemand" >
					<convert type="TemplatedMultiContent" >
					{
						"template": [MultiContentEntryText(pos=(10, 1), size=(340, 30), \
								font=0, flags=RT_HALIGN_LEFT|RT_VALIGN_CENTER, text=0)],
						"fonts": [gFont("Regular", 20)],
						"itemHeight": 30
					}
					</convert>
				</widget>
				<widget name="thumbnail" position="360,70" size="300,170" transparent="1" alphatest="on" />
				<ePixmap position="124,251" size="140,40" pixmap="skin_default/buttons/red.png" \
					transparent="1" alphatest="on" />
				<ePixmap position="408,251" size="140,40" pixmap="skin_default/buttons/green.png" \
					transparent="1" alphatest="on" />
				<widget source="key_red" render="Label" position="130,258" zPosition="2" size="148,30" \
					valign="center" halign="center" font="Regular;22" transparent="1" />
				<widget source="key_green" render="Label" position="400,258" zPosition="2" size="148,30" \
					valign="center" halign="center" font="Regular;22" transparent="1" />
			</screen>"""

	def __init__(self, session, res):
		Screen.__init__(self, session)
		self.setTitle(_('Blu-ray player'))
		self.session = session
		self.res = res
		self.name = ''
		self.closeScreen = False
		self['key_red'] = StaticText(_('Exit'))
		self['key_green'] = StaticText(_('Ok'))
		self['actions'] = ActionMap(['OkCancelActions', 'ColorActions'],
				{
					'cancel': self.Exit,
					'red': self.Exit,
					'ok': self.Ok,
					'green': self.Ok,
				})
		self['list'] = List([])
		self['name'] = Label()
		self['thumbnail'] = Pixmap()
		self.Timer = eTimer()
		self.Timer.timeout.callback.append(self.enableCloseScreen)

		content = []
		x = 1
		try:
			for title in blurayinfo.getTitles(self.res):
				title_entry = _('%d. Duration %d:%02d minutes') % \
						(x, title[0] / (45000 * 60), (title[0] / 45000) % 60)
				playfile = os.path.join(self.res, 'BDMV/STREAM/', title[1] + '.m2ts')
				languages = title[2][1:].split('/')
				codecs = title[3][1:].split('/')
				content.append((title_entry, playfile, languages, codecs))
				x += 1
		except Exception as e:
			print '[BlurayPlayer] blurayinfo.getTitles:', e
			content.append((_('Error in reading titles...'), None, None))
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
				self.name = self.res.rsplit('/', 1)[1].replace('Bluray_', '')
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

	def FinishDecode(self, picInfo=None):
		ptr = self.picloads.getData()
		if ptr:
			self['thumbnail'].instance.setPixmap(ptr.__deref__())
			del self.picloads

	def Ok(self):
		current = self['list'].getCurrent()
		if current and current[1]:
			ref = eServiceReference(3, 0, current[1])
			ref.setName('%s - %s' % (self.name, current[1][-10:]))
			self.Timer.start(20000, True)
			self.session.openWithCallback(self.MoviePlayerCallback,
					BlurayPlayer, service=ref, languages=current[2], codecs=current[3])

	def enableCloseScreen(self):
		self.closeScreen = True

	def MoviePlayerCallback(self):
		if self.closeScreen:
			self.Exit()
		else:
			self.Timer.stop()

	def Exit(self):
		if '/media/Bluray_' in self.res:
			Console().ePopen('umount -f %s' % self.res, self.umountIsoCallback)
		else:
			self.close()

	def umountIsoCallback(self, result, retval, extra_args):
		try:
			os.rmdir(self.res)
		except Exception as e:
			print '[BlurayPlayer] Cannot remove', self.res, e
		self.close()
