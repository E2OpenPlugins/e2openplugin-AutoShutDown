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
from Components.config import config, getConfigListEntry, ConfigSubsection, ConfigSelection, ConfigEnableDisable, ConfigYesNo, ConfigInteger, ConfigText, NoSave, ConfigNothing, ConfigIP
from Components.ConfigList import ConfigListScreen
from Components.FileList import FileList
from Components.Label import Label
from Components.Sources.StaticText import StaticText
from enigma import eTimer, iRecordableService, eActionMap, eServiceReference
import NavigationInstance
from os import path as os_path, system
from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Tools import Notifications
from time import time
import Screens.Standby
from __init__ import _

config.autoshutdown = ConfigSubsection()
config.autoshutdown.time = ConfigInteger(default = 120, limits = (1, 1440))
config.autoshutdown.inactivetime = ConfigInteger(default = 300, limits = (1, 1440))
config.autoshutdown.autostart = ConfigEnableDisable(default = False)
config.autoshutdown.enableinactivity = ConfigEnableDisable(default = False)
config.autoshutdown.inactivityaction = ConfigSelection(default = "standby", choices = [("standby", _("Standby")), ("deepstandby", _("Deepstandby"))])
config.autoshutdown.inactivitymessage = ConfigYesNo(default = True)
config.autoshutdown.messagetimeout = ConfigInteger(default = 20, limits = (1, 99))
config.autoshutdown.epgrefresh = ConfigYesNo(default = True)
config.autoshutdown.plugin = ConfigYesNo(default = False)
config.autoshutdown.play_media = ConfigYesNo(default = False)
config.autoshutdown.media_file = ConfigText(default = "")
config.autoshutdown.disable_at_ts = ConfigYesNo(default = False)
config.autoshutdown.disable_net_device = ConfigYesNo(default = False)
config.autoshutdown.net_device = ConfigIP(default = [0,0,0,0])


config.autoshutdown.fake_entry = NoSave(ConfigNothing())

def checkIP(ip_address):
	ip_address = "%s.%s.%s.%s" % (ip_address[0], ip_address[1], ip_address[2], ip_address[3])
	ping_ret = system("ping -q -w1 -c1 " + ip_address)
	if ping_ret == 0:
		return True
	else:
		return False

class AutoShutDownActions:
	
	def __init__(self):
		self.oldservice = None
	
	def enterShutDown(self):
		if config.autoshutdown.epgrefresh.value == True:
			if os_path.exists("/usr/lib/enigma2/python/Plugins/Extensions/EPGRefresh/EPGRefresh.py"):
				from Plugins.Extensions.EPGRefresh.EPGRefreshTimer import checkTimespan
				if not checkTimespan(
						config.plugins.epgrefresh.begin.value,
						config.plugins.epgrefresh.end.value):
					print "[AutoShutDown] not in EPGRefresh time span => ShutDown"
					self.doShutDown()
				else:
					print "[AutoShutDown] in EPGRefresh time span => restart of Timer"
					self.cancelShutDown()
			else:
				print "[AutoShutDown] ShutDown STB"
				self.doShutDown()
		else:
			print "[AutoShutDown] ShutDown STB"
			self.doShutDown()
	
	def cancelShutDown(self):
		from Screens.Standby import inStandby
		if not inStandby:
			self.stopKeyTimer()
			self.startKeyTimer()
		else:
			self.stopTimer()
			self.startTimer()
	
	def doShutDown(self):
		if config.autoshutdown.disable_net_device.value and checkIP(config.autoshutdown.net_device.value):
			print "[AutoShutDown] network device is not down  --> ignore shutdown callback"
			self.cancelShutDown()
		else:
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
		do_action = True
		
		if config.autoshutdown.inactivityaction.value == "deepstandby"  and config.autoshutdown.disable_net_device.value and checkIP(config.autoshutdown.net_device.value):
			print "[AutoShutDown] network device is not down  --> ignore shutdown callback"
			do_action = False
		
		if config.autoshutdown.disable_at_ts.value:
			running_service = session.nav.getCurrentService()
			timeshift_service = running_service and running_service.timeshift()
			
			if timeshift_service and timeshift_service.isTimeshiftActive():
				print "[AutoShutDown] inactivity timer end but timeshift is active --> ignore inactivity action"
				do_action = False
			
		if do_action:
			if config.autoshutdown.inactivitymessage.value == True:
				self.asdkeyaction = None
				if config.autoshutdown.inactivityaction.value == "standby":
					self.asdkeyaction = _("Go to standby")
				elif config.autoshutdown.inactivityaction.value == "deepstandby":
					self.asdkeyaction = _("Power off STB")
				if config.autoshutdown.play_media.value and os_path.exists(config.autoshutdown.media_file.value):
					current_service = session.nav.getCurrentlyPlayingServiceReference()
					if self.oldservice is None:
						self.oldservice = current_service
					media_service = eServiceReference(4097, 0, config.autoshutdown.media_file.value)
					session.nav.playService(media_service)
				session.openWithCallback(shutdownactions.actionEndKeyTimer, MessageBox, _("AutoShutDown: %s ?") % self.asdkeyaction, MessageBox.TYPE_YESNO, timeout=config.autoshutdown.messagetimeout.value)
			else:
				res = True
				shutdownactions.actionEndKeyTimer(res)
		else:
			self.startKeyTimer()
	
	def actionEndKeyTimer(self, res):
		if config.autoshutdown.play_media.value and os_path.exists(config.autoshutdown.media_file.value):
			session.nav.playService(self.oldservice)
		
		if res == True:
			if config.autoshutdown.inactivityaction.value == "standby":
				print "[AutoShutDown] inactivity timer end => go to standby"
				self.enterStandBy()
			elif config.autoshutdown.inactivityaction.value == "deepstandby":
				print "[AutoShutDown] inactivity timer end => shutdown"
				self.enterShutDown()
		else:
			if config.autoshutdown.play_media.value and os_path.exists(config.autoshutdown.media_file.value):
				self.oldservice = None

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
				PluginDescriptor(name=_("AutoShutDown Setup"), description=_("configure automated power off / standby"), where = PluginDescriptor.WHERE_MENU, fnc=startSetup),
				PluginDescriptor(name=_("AutoShutDown Setup"), description=_("configure automated power off / standby"), where = PluginDescriptor.WHERE_PLUGINMENU, icon="autoshutdown.png", fnc=main),
				PluginDescriptor(name=_("AutoShutDown Setup"), description=_("configure automated power off / standby"), where = PluginDescriptor.WHERE_EXTENSIONSMENU, fnc=main)]
		else:
			return [PluginDescriptor(where = [PluginDescriptor.WHERE_SESSIONSTART, PluginDescriptor.WHERE_AUTOSTART], fnc = autostart),
				PluginDescriptor(name=_("AutoShutDown Setup"), description=_("configure automated power off / standby"), where = PluginDescriptor.WHERE_MENU, fnc=startSetup)]

class AutoShutDownConfiguration(Screen, ConfigListScreen):
	skin = """
		<screen position="center,center" size="650,500" title="AutoShutDown" >
		<widget name="config" position="10,10" size="630,350" scrollbarMode="showOnDemand" />
		<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/SystemPlugins/AutoShutDown/pic/button_red.png" zPosition="2" position="10,470" size="25,25" alphatest="on" />
		<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/SystemPlugins/AutoShutDown/pic/button_green.png" zPosition="2" position="150,470" size="25,25" alphatest="on" />
		<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/SystemPlugins/AutoShutDown/pic/button_yellow.png" zPosition="2" position="240,470" size="25,25" alphatest="on" />
		<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/SystemPlugins/AutoShutDown/pic/shutdown.png" zPosition="2" position="275,360" size="100,100" alphatest="blend" />
		<widget name="buttonred" position="40,472" size="100,20" valign="center" halign="left" zPosition="2" foregroundColor="white" font="Regular;18"/>
		<widget name="buttongreen" position="180,472" size="70,20" valign="center" halign="left" zPosition="2" foregroundColor="white" font="Regular;18"/>
		<widget name="buttonyellow" position="270,472" size="100,20" valign="center" halign="left" zPosition="2" foregroundColor="white" font="Regular;18"/>
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
				"ok": self.keyOk,
			}, -2)

	def createConfigList(self):
		self.get_media = getConfigListEntry(_("Choose media file") + " (" + config.autoshutdown.media_file.value + ")", config.autoshutdown.fake_entry)
		self.list = []
		self.list.append(getConfigListEntry(_("Enable AutoShutDown:"), config.autoshutdown.autostart))
		if config.autoshutdown.autostart.value == True:
			self.list.append(getConfigListEntry(_("Time in standby for power off (min):"), config.autoshutdown.time))
		self.list.append(getConfigListEntry(_("Enable action after inactivity:"), config.autoshutdown.enableinactivity))
		if config.autoshutdown.enableinactivity.value == True:
			self.list.append(getConfigListEntry(_("Time for inactivity (min):"), config.autoshutdown.inactivetime))
			self.list.append(getConfigListEntry(_("Action for inactivity:"), config.autoshutdown.inactivityaction))
			self.list.append(getConfigListEntry(_("Disable inactivity action at timeshift:"), config.autoshutdown.disable_at_ts))
			self.list.append(getConfigListEntry(_("Show message before inactivity action:"), config.autoshutdown.inactivitymessage))
			if config.autoshutdown.inactivitymessage.value == True:
				self.list.append(getConfigListEntry(_("Message timeout (sec):"), config.autoshutdown.messagetimeout))
				self.list.append(getConfigListEntry(_("Play media file before inactivity action:"), config.autoshutdown.play_media))
				if config.autoshutdown.play_media.value:
					self.list.append(self.get_media)
		if config.autoshutdown.enableinactivity.value or config.autoshutdown.autostart.value:
			self.list.append(getConfigListEntry(_("Disable shutdown in EPGRefresh time span:"), config.autoshutdown.epgrefresh))
			self.list.append(getConfigListEntry(_("Disable shutdown until a given device is pingable:"), config.autoshutdown.disable_net_device))
			if config.autoshutdown.disable_net_device.value:
				self.list.append(getConfigListEntry(_("IP address of network device:"), config.autoshutdown.net_device))
		self.list.append(getConfigListEntry(_("Show in Extensions/Plugins:"), config.autoshutdown.plugin))

	def changedEntry(self):
		shutdownactions.stopKeyTimer()
		self.createConfigList()
		self["config"].setList(self.list)
		shutdownactions.startKeyTimer()

	def setWindowTitle(self):
		self.setTitle(_("AutoShutDown Setup"))

	def keyOk(self):
		if self["config"].getCurrent() == self.get_media:
			start_dir = "/media/"
			self.session.openWithCallback(self.selectedMediaFile,AutoShutDownFile, start_dir)

	def selectedMediaFile(self, res):
		if res is not None:
			config.autoshutdown.media_file.value = res
			config.autoshutdown.media_file.save()
			self.changedEntry()

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
			config.autoshutdown.autostart.setValue(0)
			config.autoshutdown.enableinactivity.setValue(0)
			config.autoshutdown.inactivetime.setValue(300)
			config.autoshutdown.inactivityaction.setValue("standby")
			config.autoshutdown.epgrefresh.setValue(1)
			config.autoshutdown.plugin.setValue(0)
			config.autoshutdown.inactivitymessage.setValue(1)
			config.autoshutdown.messagetimeout.setValue(20)
			config.autoshutdown.play_media.setValue(0)
			config.autoshutdown.media_file.setValue("")
			config.autoshutdown.disable_at_ts.setValue(0)
			config.autoshutdown.disable_net_device.setValue(0)
			config.autoshutdown.net_device.setValue([0,0,0,0])
			self.save()
			self.close(True,self.session)

class AutoShutDownFile(Screen):
	skin = """
		<screen name="AutoShutDownFile" position="center,center" size="650,450" title="Select a media file for AutoShutDown">
			<widget name="media" position="10,10" size="540,30" valign="top" font="Regular;22" />
			<widget name="filelist" position="10,45" zPosition="1" size="540,350" scrollbarMode="showOnDemand"/>
			<widget render="Label" source="key_red" position="40,422" size="100,20" valign="center" halign="left" zPosition="2" font="Regular;18" foregroundColor="white" />
			<widget render="Label" source="key_green" position="180,422" size="70,20" valign="center" halign="left" zPosition="2" font="Regular;18" foregroundColor="white" />
			<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/SystemPlugins/AutoShutDown/pic/button_red.png" zPosition="2" position="10,420" size="25,25" alphatest="on" />
			<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/SystemPlugins/AutoShutDown/pic/button_green.png" zPosition="2" position="150,420" size="25,25" alphatest="on" />
		</screen>
		"""

	def __init__(self, session, initDir, plugin_path = None):
		Screen.__init__(self, session)
		#self.skin_path = plugin_path
		self["filelist"] = FileList(initDir, inhibitMounts = False, inhibitDirs = False, showMountpoints = False)
		self["media"] = Label()
		self["actions"] = ActionMap(["WizardActions", "DirectionActions", "ColorActions", "EPGSelectActions"],
		{
			"back": self.cancel,
			"left": self.left,
			"right": self.right,
			"up": self.up,
			"down": self.down,
			"ok": self.ok,
			"green": self.green,
			"red": self.cancel
			
		}, -1)
		self.title=_("Select a media file for AutoShutDown")
		try:
			self["title"]=StaticText(self.title)
		except:
			print 'self["title"] was not found in skin'	
		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("OK"))

	def cancel(self):
		self.close(None)

	def green(self):
		if self["filelist"].getSelection()[1] == True:
			self["media"].setText(_("Invalid Choice"))
		else:
			directory = self["filelist"].getCurrentDirectory()
			if (directory.endswith("/")):
				self.fullpath = self["filelist"].getCurrentDirectory() + self["filelist"].getFilename()
			else:
				self.fullpath = self["filelist"].getCurrentDirectory() + "/" + self["filelist"].getFilename()
		  	self.close(self.fullpath)

	def up(self):
		self["filelist"].up()
		self.updateFile()

	def down(self):
		self["filelist"].down()
		self.updateFile()

	def left(self):
		self["filelist"].pageUp()
		self.updateFile()

	def right(self):
		self["filelist"].pageDown()
		self.updateFile()

	def ok(self):
		if self["filelist"].canDescent():
			self["filelist"].descent()
			self.updateFile()

	def updateFile(self):
		currFolder = self["filelist"].getSelection()[0]
		if self["filelist"].getFilename() is not None:
			directory = self["filelist"].getCurrentDirectory()
			if (directory.endswith("/")):
				self.fullpath = self["filelist"].getCurrentDirectory() + self["filelist"].getFilename()
			else:
				self.fullpath = self["filelist"].getCurrentDirectory() + "/" + self["filelist"].getFilename()
			
			self["media"].setText(self["filelist"].getFilename())
		else:
			currFolder = self["filelist"].getSelection()[0]
			if currFolder is not None:
				self["media"].setText(currFolder)
			else:
				self["media"].setText(_("Invalid Choice"))
