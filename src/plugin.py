# -*- coding: utf-8 -*-

# maintainer: <plnick@vuplus-support.org>

#This plugin is free software, you are allowed to
#modify it (if you keep the license),
#but you are not allowed to distribute/publish
#it without source code (this version and your modifications).
#This means you also have to distribute
#source code of your modifications.
#autoshutdown.png <from http://www.everaldo.com>

from Components.ActionMap import ActionMap
from Components.config import config, getConfigListEntry, ConfigSubsection, ConfigSelection, ConfigEnableDisable, ConfigYesNo, ConfigInteger
from Components.Label import Label
from Components.ConfigList import ConfigListScreen
from enigma import eTimer, iRecordableService, eActionMap
import NavigationInstance
from os import path as os_path
from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Tools import Notifications
from time import time
import Screens.Standby
from __init__ import _

config.autoshutdown = ConfigSubsection()
config.autoshutdown.time = ConfigInteger(default = 120, limits = (1, 1440))
config.autoshutdown.inactivetime = ConfigInteger(default = 60, limits = (1, 1440))
config.autoshutdown.autostart = ConfigEnableDisable(default=True)
config.autoshutdown.enableinactivity = ConfigEnableDisable(default=True)
config.autoshutdown.inactivityaction = ConfigSelection(default = "standby", choices = [("standby", _("Standby")), ("deepstandby", _("Deepstandby"))])
config.autoshutdown.inactivitymessage = ConfigYesNo(default=True)
config.autoshutdown.messagetimeout = ConfigInteger(default = 5, limits = (1, 60))
config.autoshutdown.epgrefresh = ConfigYesNo(default=True)
config.autoshutdown.plugin = ConfigYesNo(default=True)

class AutoShutDownActions:
	def enterShutDown(self):
		if config.autoshutdown.epgrefresh.value == True:
			if os_path.exists("/usr/lib/enigma2/python/Plugins/Extensions/EPGRefresh/EPGRefresh.py"):
				from Plugins.Extensions.EPGRefresh.EPGRefreshTimer import checkTimespan
				if not checkTimespan(
						config.plugins.epgrefresh.begin.value,
						config.plugins.epgrefresh.end.value):
					print "[AutoShutDown] not in EPGRefresh time span => ShutDown"
					session.open(Screens.Standby.TryQuitMainloop,1)
				else:
					print "[AutoShutDown] in EPGRefresh time span => restart of Timer"
					from Screens.Standby import inStandby
					if not inStandby:
						self.stopKeyTimer()
						self.startKeyTimer()
					else:
						self.stopTimer()
						self.startTimer()
			else:
				print "[AutoShutDown] ShutDown VU+ STB"
				session.open(Screens.Standby.TryQuitMainloop,1)
		else:
			print "[AutoShutDown] ShutDown VU+ STB"
			session.open(Screens.Standby.TryQuitMainloop,1)

	def enterStandBy(self):
		print "[AutoShutDown] STANDBY . . . "
		Notifications.AddNotification(Screens.Standby.Standby)

	def startTimer(self):
		if config.autoshutdown.autostart.value == True:
			print "[AutoShutDown] Starting ShutDownTimer"
			shutdowntime = config.autoshutdown.time.value*60000
			self.AutoShutDownTimer = eTimer()
			self.AutoShutDownTimer.start(shutdowntime, True)
			self.AutoShutDownTimer.callback.append(shutdownactions.enterShutDown)

	def stopTimer(self):
		try:
			if self.AutoShutDownTimer.isActive():
				print "[AutoShutDown] Stopping ShutDownTimer"
				self.AutoShutDownTimer.stop()
		except:
			print "[AutoShutDown] No ShutDownTimer to stop"

	def startKeyTimer(self):
		if config.autoshutdown.enableinactivity.value == True:
			inactivetime = config.autoshutdown.inactivetime.value*60000
			self.AutoShutDownKeyTimer = eTimer()
			self.AutoShutDownKeyTimer.start(inactivetime, True)
			self.AutoShutDownKeyTimer.callback.append(shutdownactions.endKeyTimer)

	def stopKeyTimer(self):
		try:
			self.AutoShutDownKeyTimer.stop()
		except:
			print "[AutoShutDown] No inactivity timer to stop"

	def endKeyTimer(self):
		if config.autoshutdown.inactivitymessage.value == True:
			self.asdkeyaction = None
			if config.autoshutdown.inactivityaction.value == "standby":
				self.asdkeyaction = _("Go to standby")
			elif config.autoshutdown.inactivityaction.value == "deepstandby":
				self.asdkeyaction = _("Power off VU+ STB")
			session.openWithCallback(shutdownactions.actionEndKeyTimer, MessageBox, _("AutoShutDown: %s ?") % self.asdkeyaction, MessageBox.TYPE_YESNO, timeout=config.autoshutdown.messagetimeout.value)
		else:
			res = True
			shutdownactions.actionEndKeyTimer(res)

	def actionEndKeyTimer(self, res):
		if res == True:
			if config.autoshutdown.inactivityaction.value == "standby":
				print "[AutoShutDown] inactivity timer end => go to standby"
				self.enterStandBy()
			elif config.autoshutdown.inactivityaction.value == "deepstandby":
				print "[AutoShutDown] inactivity timer end => shutdown"
				self.enterShutDown()

shutdownactions = AutoShutDownActions()

def autostart(reason, **kwargs):
	global session
	if kwargs.has_key("session") and reason == 0:
		session = kwargs["session"]
		print "[AutoShutDown] start...."
		config.misc.standbyCounter.addNotifier(standbyCounterChanged, initial_call = False)
		## from InfoBarGenerics.py
		eActionMap.getInstance().bindAction('', -0x7FFFFFFF, keyPressed)
		##
		shutdownactions.startKeyTimer()

def keyPressed(key, flag):
	if config.autoshutdown.enableinactivity.value == True:
		from Screens.Standby import inStandby
		if not inStandby:
			if flag == 1:
				shutdownactions.stopKeyTimer()
				shutdownactions.startKeyTimer()
	return 0

def standbyCounterChanged(configElement):
	print "[AutoShutDown] got to standby . . ."
	if leaveStandby not in Screens.Standby.inStandby.onClose:
		Screens.Standby.inStandby.onClose.append(leaveStandby)
	shutdownactions.startTimer()
	shutdownactions.stopKeyTimer()

def leaveStandby():
	print "[AutoShutDown] leave standby . . ."
	shutdownactions.stopTimer()
	shutdownactions.startKeyTimer()

def main(session, **kwargs):
	print "[AutoShutDown] Open Configuration"
	session.open(AutoShutDownConfiguration)

def startSetup(menuid):
	if menuid != "system":
		return [ ]
	return [(_("AutoShutDown settings") , main, "autoshutdown_setup", 60)]

def Plugins(**kwargs):
		if config.autoshutdown.plugin.value:
			return [PluginDescriptor(where = [PluginDescriptor.WHERE_SESSIONSTART, PluginDescriptor.WHERE_AUTOSTART], fnc = autostart),
				PluginDescriptor(name=_("AutoShutDown Setup"), description=_("AutoShutDown for VU+"), where = PluginDescriptor.WHERE_MENU, fnc=startSetup),
				PluginDescriptor(name=_("AutoShutDown Setup"), description=_("AutoShutDown for VU+"), where = PluginDescriptor.WHERE_PLUGINMENU, icon="autoshutdown.png", fnc=main),
				PluginDescriptor(name=_("AutoShutDown Setup"), description=_("AutoShutDown for VU+"), where = PluginDescriptor.WHERE_EXTENSIONSMENU, fnc=main)]
		else:
			return [PluginDescriptor(where = [PluginDescriptor.WHERE_SESSIONSTART, PluginDescriptor.WHERE_AUTOSTART], fnc = autostart),
				PluginDescriptor(name=_("AutoShutDown Setup"), description=_("AutoShutDown for VU+"), where = PluginDescriptor.WHERE_MENU, fnc=startSetup)]

class AutoShutDownConfiguration(Screen, ConfigListScreen):
	skin = """
		<screen position="center,center" size="650,400" title="AutoShutDown for VU+" >
		<widget name="config" position="10,10" size="630,350" scrollbarMode="showOnDemand" />
		<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/SystemPlugins/AutoShutDown/pic/button_red.png" zPosition="2" position="10,370" size="25,25" alphatest="on" />
		<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/SystemPlugins/AutoShutDown/pic/button_green.png" zPosition="2" position="150,370" size="25,25" alphatest="on" />
		<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/SystemPlugins/AutoShutDown/pic/button_yellow.png" zPosition="2" position="240,370" size="25,25" alphatest="on" />
		<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/SystemPlugins/AutoShutDown/pic/shutdown.png" zPosition="2" position="275,250" size="100,100" alphatest="blend" />
		<widget name="buttonred" position="40,372" size="100,20" valign="center" halign="left" zPosition="2" foregroundColor="white" font="Regular;18"/>
		<widget name="buttongreen" position="180,372" size="70,20" valign="center" halign="left" zPosition="2" foregroundColor="white" font="Regular;18"/>
		<widget name="buttonyellow" position="270,372" size="100,20" valign="center" halign="left" zPosition="2" foregroundColor="white" font="Regular;18"/>
		</screen>"""

	def __init__(self, session, args = 0):
		self.session = session
		Screen.__init__(self, session)

		self.createConfigList()
		self.onShown.append(self.setWindowTitle)
		ConfigListScreen.__init__(self, self.list, session = self.session, on_change = self.changedEntry)

		self["buttonred"] = Label(_("Exit"))
		self["buttongreen"] = Label(_("OK"))
		self["buttonyellow"] = Label(_("Default"))
		self["setupActions"] = ActionMap(["SetupActions", "ColorActions"],
			{
				"green": self.save,
				"red": self.cancel,
				"yellow": self.revert,
				"save": self.save,
				"cancel": self.cancel,
				"ok": self.save,
			}, -2)

	def createConfigList(self):
		self.list = []
		self.list.append(getConfigListEntry(_("Enable AutoShutDown:"), config.autoshutdown.autostart))
		if config.autoshutdown.autostart.value == True:
			self.list.append(getConfigListEntry(_("Time in standby for power off (min):"), config.autoshutdown.time))
		self.list.append(getConfigListEntry(_("Enable action after inactivity:"), config.autoshutdown.enableinactivity))
		if config.autoshutdown.enableinactivity.value == True:
			self.list.append(getConfigListEntry(_("Time for inactivity (min):"), config.autoshutdown.inactivetime))
			self.list.append(getConfigListEntry(_("Action for inactivity:"), config.autoshutdown.inactivityaction))
			self.list.append(getConfigListEntry(_("Show message before inactivity action:"), config.autoshutdown.inactivitymessage))
			if config.autoshutdown.inactivitymessage.value == True:
				self.list.append(getConfigListEntry(_("Message timeout (sec):"), config.autoshutdown.messagetimeout))
		self.list.append(getConfigListEntry(_("Disable shutdown in EPGRefresh time span:"), config.autoshutdown.epgrefresh))
		self.list.append(getConfigListEntry(_("Show in Extensions/Plugins:"), config.autoshutdown.plugin))

	def changedEntry(self):
		shutdownactions.stopKeyTimer()
		self.createConfigList()
		self["config"].setList(self.list)
		shutdownactions.startKeyTimer()

	def setWindowTitle(self):
		self.setTitle(_("AutoShutDown Setup for VU+ STB"))

	def save(self):
		shutdownactions.stopKeyTimer()
		for x in self["config"].list:
			x[1].save()
		self.changedEntry()
		shutdownactions.startKeyTimer()
		self.close()

	def cancel(self):
		if self["config"].isChanged():
			self.session.openWithCallback(self.cancelConfirm, MessageBox, _("Really close without saving settings?"), MessageBox.TYPE_YESNO, default = False)
		else:
			for x in self["config"].list:
				x[1].cancel()
			self.close(False,self.session)

	def cancelConfirm(self, result):
		if result is None or result is False:
			print "[AutoShutDown] Cancel not confirmed."
		else:
			print "[AutoShutDown] Cancel confirmed. Configchanges will be lost."
			for x in self["config"].list:
				x[1].cancel()
			self.close(False,self.session)

	def revert(self):
		self.session.openWithCallback(self.keyYellowConfirm, MessageBox, _("Reset AutoShutDown settings to defaults?"), MessageBox.TYPE_YESNO, timeout = 20, default = False)

	def keyYellowConfirm(self, confirmed):
		if not confirmed:
			print "[AutoShutDown] Reset to defaults not confirmed."
		else:
			print "[AutoShutDown] Setting Configuration to defaults."
			config.autoshutdown.time.setValue(120)
			config.autoshutdown.autostart.setValue(1)
			config.autoshutdown.enableinactivity.setValue(1)
			config.autoshutdown.inactivetime.setValue(60)
			config.autoshutdown.inactivityaction.setValue("standby")
			config.autoshutdown.epgrefresh.setValue(1)
			config.autoshutdown.plugin.setValue(1)
			config.autoshutdown.inactivitymessage.setValue(1)
			config.autoshutdown.messagetimeout.setValue(5)
			self.save()
			self.close(True,self.session)
