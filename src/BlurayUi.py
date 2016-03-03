import os

from enigma import eServiceReference
from Components.ActionMap import ActionMap
from Components.config import config
from Components.Console import Console
from Components.Label import Label
from Components.Sources.List import List
from Components.Sources.StaticText import StaticText
from Plugins.Plugin import PluginDescriptor
from Screens.InfoBar import InfoBar, MoviePlayer
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from Tools.BoundFunction import boundFunction

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

	def getPluginList(self):
		from Components.PluginComponent import plugins
		list = []
		for p in plugins.getPlugins(where=PluginDescriptor.WHERE_EXTENSIONSMENU):
			if p.name != _('Blu-ray player'):
				list.append(((boundFunction(self.getPluginName, p.name),
					boundFunction(self.runPlugin, p), lambda: True), None))
		return list


class BlurayMain(Screen):
	skin = """
		<screen position="center,center" size="640,370">
			<widget name="info" position="center,10" size="620,60" halign="center" font="Regular;22" />
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
		self['info'] = Label()
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

	def Ok(self):
		current = self['list'].getCurrent()
		if current and current[1]:
			playref = current[1]
			ref = eServiceReference(3, 0, playref)
			ref.setName(playref.rsplit('/BDMV')[0].rsplit('/')[1])
			print '[BlurayPlayer] Play:', playref
			self.session.openWithCallback(self.MoviePlayerCallback, BlurayPlayer, ref)

	def MoviePlayerCallback(self):
		if self.res == '/media/bluray':
			Console().ePopen('umount -f /media/bluray')
			try:
				os.rmdir('/media/bluray')
			except Exception as e:
				print '[BlurayPlayer] remove directory /media/bluray:', e
		self.close()
