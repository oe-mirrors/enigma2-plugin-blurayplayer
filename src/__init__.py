from os import environ
from gettext import bindtextdomain, dgettext, gettext

from Components.Language import language
from Tools.Directories import resolveFilename, SCOPE_PLUGINS


def localeInit():
	environ['LANGUAGE'] = language.getLanguage()[:2]
	bindtextdomain('BlurayPlayer', resolveFilename(SCOPE_PLUGINS,
		'Extensions/BlurayPlayer/locale'))


def _(txt):
	t = dgettext('BlurayPlayer', txt)
	if t == txt:
		t = gettext(txt)
	return t


localeInit()
language.addCallback(localeInit)
