from Components.config import config, getConfigListEntry, \
	ConfigNothing, ConfigSelection, ConfigOnOff
from Components.PluginComponent import plugins
from Components.SystemInfo import SystemInfo
from Plugins.Plugin import PluginDescriptor
from Screens.AudioSelection import AudioSelection
from Tools.ISO639 import LanguageCodes

from . import _


class BlurayAudioSelection(AudioSelection):
	def __init__(self, session, infobar, languages, codecs):
		page = 'audio'
		AudioSelection.__init__(self, session, infobar, page)
		self.skinName = 'AudioSelection'
		self.languages = languages
		self.codecs = codecs
		self.codecs.append('')

	def fillList(self, arg=None):
		streams = []
		conflist = []
		selectedidx = 0

		self['key_blue'].setBoolean(False)

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

			lang_len = len(self.languages)
			lang_dif = lang_len - n
			li = 0

			for x in range(n):
				number = str(x + 1)
				i = audio.getTrackInfo(x)
				languages = i.getLanguage().split('/')
				description = i.getDescription() or ''
				selected = ''
				language = ''

				if lang_dif and description:
					while li < lang_len and self.codecs[li] != description:
						li += 1
				if li >= lang_len:
					li = x
				else:
					if not languages[0]:
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
