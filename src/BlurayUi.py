import os

from enigma import eServiceReference
from Components.ActionMap import ActionMap
from Components.Console import Console
from Components.Label import Label
from Components.Sources.List import List
from Components.Sources.StaticText import StaticText
from Screens.InfoBar import InfoBar, MoviePlayer
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen

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


class BlurayMain(Screen):
	skin = """
		<screen position="center,center" size="640,370">
			<widget name="name" position="center,10" size="620,60" halign="center" font="Regular;30" />
			<widget source="list" render="Listbox" position="10,70" size="620,240" \
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
			<ePixmap position="114,321" size="140,40" pixmap="skin_default/buttons/red.png" \
				transparent="1" alphatest="on" />
			<ePixmap position="378,321" size="140,40" pixmap="skin_default/buttons/green.png" \
				transparent="1" alphatest="on" />
			<widget source="key_red" render="Label" position="110,328" zPosition="2" size="148,30" \
				valign="center" halign="center" font="Regular;22" transparent="1" />
			<widget source="key_green" render="Label" position="370,328" zPosition="2" size="148,30" \
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
		# Generate titles
		content = []
		x = 1
		try:
			for title in blurayinfo.getTitles(self.res):
				duration = title[0]
				clip_id = title[1]
				playfile = os.path.join(self.res, 'BDMV/STREAM/', clip_id + '.m2ts')
				title_entry = _('%d. Duration %d:%02d minutes') % \
					(x, duration / (45000 * 60), (duration / 45000) % 60)
				content.append((title_entry, playfile))
				x += 1
		except Exception as e:
			print '[BlurayPlayer] blurayinfo.getTitles:', e
			content.append((_('Error in reading tiles!'), None))
		self['list'].setList(content)
		# Set name
		content = os.path.join(self.res, 'BDMV/META/DL/')
		if os.path.exists(content):
			for x in os.listdir(content):
				if x[-4:] == '.xml':
					try:
						self.name = open(os.path.join(content, x)).read().split('<di:name>')[1].split('</di:name>')[0]
					except:
						pass
		if not self.name:
			if self.res[-1:] == '/':
				self.res = self.res[:-1]
			try:
				self.name = self.res.rsplit('/', 1)[1]
			except:
				pass
		self['name'].setText(self.name)

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
