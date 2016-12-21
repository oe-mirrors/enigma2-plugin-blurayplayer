from Screens.AudioSelection import AudioSelection
from Tools.ISO639 import LanguageCodes

from . import _


class BlurayAudioSelection(AudioSelection):
	def __init__(self, session, infobar, languages, codecs):
		page = 'audio'
		AudioSelection.__init__(self, session, infobar, page)
		self.skinName = ['BlurayAudioSelection', 'AudioSelection']
		self.languages = languages
		self.codecs = codecs
		self.codecs.append('')

	def fillList(self, arg=None):
		AudioSelection.fillList(self, arg)
		service = self.session.nav.getCurrentService()
		audio = service and service.audioTracks()
		n = audio and audio.getNumberOfTracks() or 0

		if n > 0:
			streams = []
			selectedidx = 0
			selectedAudio = audio.getCurrentTrack()
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

			self['streams'].list = streams
			self['streams'].setIndex(selectedidx)
