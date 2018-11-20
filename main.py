# -*- coding: utf-8 -*-

import sys
from datetime import datetime
import random
from pprint import pprint

from dpa.lib.initLocale import initLocale
initLocale()
from dpa.lib.convertCyrillic import convertCyrillic
_ = convertCyrillic("UTF-8")
del initLocale, convertCyrillic

#reload(sys)
#sys.setdefaultencoding('utf-8')

from PyQt4 import QtCore, QtGui

import icons

#from timeThis import timeThis

from api import api
API = api()

from db import create_connection, DataBase
schemeDbApi = DataBase(create_connection('scales.db'))

#reg_ex = QtCore.QRegExp(u"[а-яА-Яa-zA-Z0-9 -_.()\",/@]+")
reg_ex = QtCore.QRegExp(u"[а-яА-Яa-zA-Z0-9 _.,*]+")

colors = {0: QtGui.QColor(80, 180, 50, 255),
          1: QtGui.QColor(200, 200, 20, 255),
          2: QtGui.QColor(200, 100, 100, 255),
          #'offline': QtCore.Qt.black,
          3: QtCore.Qt.black,
          4: QtCore.Qt.gray,
          'selected': QtGui.QColor(1, 100, 200, 255),
          'registered': QtGui.QColor(0, 0, 0, 130),
          'current': QtGui.QColor(100, 150, 70, 255),
          'finished': QtGui.QColor(250, 40, 40, 255),
          #'background': QtGui.QColor(0, 0, 0, 20),
          'background': QtGui.QColor(0, 0, 0, 180),
          'link': QtGui.QColor(0, 0, 0, 50),
          'grid': QtGui.QColor(0, 0, 0, 20),
          'leader': QtGui.QColor(0, 0, 0, 50),
        }

import itertools
def count(c=itertools.count()):
  return next(c)

def fontWidth():
  if 'linux' in sys.platform:
    return 6
  else:
    return 7

class Item(QtGui.QGraphicsItem):
  def __init__(self, parent, name, X, Y, Size, scales, status=0):
    super(Item, self).__init__(None, parent.scene)
    self.parent = parent
    self.links = []
    self.lines = []
    self.type = 'agent'
    self.status = status
    self.name = name
    self.textLocation = 'down'
    self.setToolTip(name)
    self.scales = scales
    self.setFlag(QtGui.QGraphicsItem.ItemIsSelectable)
    self.setFlag(QtGui.QGraphicsItem.ItemIsMovable)
    self.setAcceptedMouseButtons(QtCore.Qt.LeftButton)
    self.setAcceptHoverEvents(True)
    self.brush = QtGui.QBrush(colors[self.status])
    self.scaleColor = [colors['registered'], colors['current'], colors['finished']]
    #self.color = color
    self.w = Size
    self.h = Size
    self.moveToCoord(X, Y)
    self.setZValue(2)
    self.font = QtGui.QFont('Courier', 8)
    #self.font.setBold(True)

  def setColor(self, monualColor=False):
    #self.parent.parent.mainTableBarCheck.setChecked(False)
    if not monualColor:
      if self.isSelected():
        self.brush = QtGui.QBrush(colors['selected'])
      else:
        #self.brush = QtGui.QBrush(self.color)
        self.brush = QtGui.QBrush(colors[self.status])
    else:
      self.brush = QtGui.QBrush(monualColor)

  def boundingRect(self):
    return QtCore.QRectF(-self.w/2, -self.h/2, self.w, self.h)

  def textMove(self, coord, rect=False, text=False):
    if self.textLocation == 'down':
      return coord
    elif self.textLocation == 'up':
      if rect:
        return -(coord+rect)
      else:
        if text:
          return -(coord-text)
        else:
          return -(coord)

  def paint(self, painter, option, widget):
    painter.setFont(self.font)
    painter.drawText(QtCore.QPointF(0, self.textMove(self.h/2+30, False, 8)), unicode(self.name))
    painter.setPen(colors['leader'])
    painter.drawLine(0, 0, 10, self.textMove(self.h/2+18))
    painter.drawRect(-2, self.textMove(self.h/2+18, 16), len(self.name)*fontWidth()+3, 16)
    painter.setBrush(self.brush)
    space = 0
    for n, i in enumerate(self.scales):
      painter.setPen(self.scaleColor[n])
      #painter.drawText(QtCore.QPointF(0, self.h/2+45+n*10), unicode(i))
      painter.drawText(QtCore.QPointF(space, self.textMove(self.h/2+45, False, 8)), unicode(i))
      space += len(str(i))*fontWidth()+15
    #painter.setPen(QtGui.QPen(self.color, 2))
    painter.setPen(QtGui.QPen(colors[self.status], 2))
    if self.w >= 70:
      painter.drawRoundedRect(self.boundingRect(), 10, 10)
    else:
      painter.drawEllipse(self.boundingRect())

  def moveToCoord(self, x, y):
    self.setX(self.grid(x))
    self.setY(self.grid(y))

  def moveToCenter(self):
    sceneRect = self.parent.mapToScene(self.parent.rect()).boundingRect()
    self.moveToCoord(sceneRect.center().x(), sceneRect.center().y())

  def hoverEnterEvent(self, event):
    cursor = QtGui.QCursor( QtCore.Qt.OpenHandCursor )
    QtGui.QApplication.instance().setOverrideCursor( cursor )

  def hoverLeaveEvent(self, event):
    QtGui.QApplication.instance().restoreOverrideCursor()
    QtGui.QApplication.instance().restoreOverrideCursor()

  def lineFollow(self):
    for agent in self.parent.scene.selectedItems():
      for line in agent.lines:
        line.follow()

  def mouseMoveEvent(self, event):
    self.lineFollow()
    QtGui.QGraphicsItem.mouseMoveEvent(self, event)

  def mouseReleaseEvent(self, event):
    for agent in self.parent.scene.selectedItems():
      agent.moveToCoord(agent.x(), agent.y())
      self.lineFollow()
      schemeDbApi.updateNode(agent.name, agent.x(), agent.y(), agent.w)
    QtGui.QGraphicsItem.mouseReleaseEvent(self, event)

  def grid(self, coord):
    s = coord % self.parent.gridSize
    if s < self.parent.gridSize/2:
      return coord - s
    else:
      return coord - s + self.parent.gridSize

class BreakingPoint(Item):
  def __init__(self, parent, name, X, Y, Size=6, scales=[], status=4):
    super(BreakingPoint, self).__init__(parent, name, X, Y, Size, scales, status)
    self.type = 'bp'
    self.setZValue(1)
    self.setToolTip('')

  def paint(self, painter, option, widget):
    painter.setBrush(self.brush)
    painter.setPen(QtGui.QPen(QtCore.Qt.gray))
    painter.drawEllipse(self.boundingRect())

class Line(QtGui.QGraphicsLineItem):
  def __init__(self, end1, end2, parent):
    super(Line, self).__init__()
    self.parent = parent
    self.type = 'line'
    self.end1 = end1
    self.end2 = end2
    self.setPen(QtGui.QPen(colors['link'], 3))
    self.setAcceptedMouseButtons(QtCore.Qt.LeftButton)
    self.setAcceptHoverEvents(True)
    self.makeToolTip()
    self.follow()

  def makeToolTip(self):
    bp = False
    for i in [self.end1.name, self.end2.name]:
      l = i.split('##')
      if l[0] == 'breakingPoint' and len(l) == 4:
        bp = True
        break
    if bp:
      self.setToolTip(u'{} - {}'.format(l[1], l[2]))
    else:
      self.setToolTip(u'{} - {}'.format(self.end1.name, self.end2.name))

  def hoverEnterEvent(self, event):
    cursor = QtGui.QCursor( QtCore.Qt.CrossCursor )
    QtGui.QApplication.instance().setOverrideCursor( cursor )

  def hoverLeaveEvent(self, event):
    QtGui.QApplication.instance().restoreOverrideCursor()
    QtGui.QApplication.instance().restoreOverrideCursor()

  def follow(self):
    self.setLine(self.end1.x(), self.end1.y(), self.end2.x(), self.end2.y())

  def mouseMoveEvent(self, event):
    self.tempLine.setLine(self.end2.x(), self.end2.y(), event.pos().x(), event.pos().y())
    self.setLine(self.end1.x(), self.end1.y(), event.pos().x(), event.pos().y())

  def mousePressEvent(self, event):
    self.tempLine = QtGui.QGraphicsLineItem(self.end2.x(), self.end2.y(), event.pos().x(), event.pos().y())
    self.tempLine.setPen(QtGui.QPen(colors['link'], 3))
    self.parent.scene.addItem(self.tempLine)

  def mouseReleaseEvent(self, event):
    QtGui.QApplication.instance().restoreOverrideCursor()
    QtGui.QApplication.instance().restoreOverrideCursor()
    self.parent.addBP(event.pos().x(), event.pos().y(), self.end1.name, self.end2.name)

class Scheme(QtGui.QGraphicsView):
  def __init__(self, parent=None):
    super(Scheme, self).__init__()
    self.parent = parent
    self.setTransformationAnchor(QtGui.QGraphicsView.AnchorUnderMouse)
    self.setDragMode(QtGui.QGraphicsView.RubberBandDrag)
    self.scene = QtGui.QGraphicsScene(self)
    self.setScene(self.scene)
    self.scene.selectionChanged.connect(self.selChanged)
    #self.scene.setBackgroundBrush(QtGui.QBrush(colors['background']))
    self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
    self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
    self.setViewportUpdateMode(QtGui.QGraphicsView.FullViewportUpdate)
    self.setRenderHints(QtGui.QPainter.Antialiasing | QtGui.QPainter.HighQualityAntialiasing)
    self.wasSelected = []
    self.gridSize = 20

  def makeTempLine(self):
    self.tempLine = QtGui.QGraphicsLineItem()
    self.tempLine.setPen(QtGui.QPen(colors['link'], 3))

  def moveTempLine(self, x1, y1, x2, y2):
    self.makeTempLine()
    self.tempLine.setLine(x1, y1, x2, y2)

  def drawBackground(self, painter, rect):
    if self.transform().m11() > 0.2:
      w = self.gridSize
      h = self.gridSize
      gr = rect.toRect()
      start_x = gr.left() + w - (gr.left() % w)
      start_y = gr.top() + h - (gr.top() % h)
      painter.save()
      painter.setPen(colors['grid'])
      for x in range(start_x, gr.right(), w):
          painter.drawLine(x, gr.top(), x, gr.bottom())
      for y in range(start_y, gr.bottom(), h):
          painter.drawLine(gr.left(), y, gr.right(), y)
      painter.restore()

  def breakingPointName(self, end1, end2):
    name1 = end1.split('##')
    name2 = end2.split('##')
    if len(name1) != 4 and len(name2) != 4:
      return u'breakingPoint##{}##{}##{}'.format(end1, end2, random.randint(0, 10000000))
    elif len(name1) == 4:
      return u'breakingPoint##{}##{}##{}'.format(name1[1], name1[2], random.randint(0, 10000000))
    elif len(name2) == 4:
      return u'breakingPoint##{}##{}##{}'.format(name2[1], name2[2], random.randint(0, 10000000))

  def addBP(self, X, Y, end1, end2):
    bpName = self.breakingPointName(end1, end2)
    BreakingPoint(self, bpName, X, Y)
    schemeDbApi.createNode(bpName, X, Y, 6)
    schemeDbApi.updateLink(end1, end2, bpName)
    schemeDbApi.createLink(end2, bpName)
    self.loadScheme()

  def removeNode(self, name):
    schemeDbApi.deleteLinks(name)
    schemeDbApi.deleteNode(name)

  def deleteItem(self):
    agentsToDel = []
    for node in self.scene.selectedItems():
      if node.type == 'agent':
        #if node.color == colors['offline']:
        if node.status == 3:
          agentsToDel.append(node.name)
      elif node.type == 'bp':
        newLink = schemeDbApi.readLinks2(node.name)
        self.removeNode(node.name)
        schemeDbApi.createLink(newLink[0], newLink[1])
    if agentsToDel:
      reply = QtGui.QMessageBox.question(self, u'Внимание!',
          u'Вы уверены, что хотите удалить выбранные агенты навсегда?', QtGui.QMessageBox.Yes, QtGui.QMessageBox.No)
      if reply == QtGui.QMessageBox.Yes:
        for agent in agentsToDel:
          bpsList = schemeDbApi.readAllBPbyNode(agent)
          for bps in bpsList:
            for bp in bps:
              self.removeNode(bp)
          self.removeNode(agent)
    self.parent.mainTable.refresh()

  def showDB(self):
    print "================= NODES ================="
    print schemeDbApi.readNodes()
    print "================= LINKS ================="
    print schemeDbApi.readAllLinks()
    print "=================  BPs  ================="
    print schemeDbApi.readBP()
    print "========================================="

  def loadBP(self):
    data = schemeDbApi.readBP()
    if len(data) > 0:
      for bpId, bpX, bpY, bpSize in data:
        BreakingPoint(self, bpId, bpX, bpY)

  def loadScheme(self):
    self.scene.clear()
    agents = API.countStatus()
    data = schemeDbApi.readNodes()
    if len(data) > 0:
      for nodeId, nodeX, nodeY, nodeSize in data:
        if nodeId in agents.keys():
          agentStatus = agents[nodeId]
          agent = Item(self, nodeId, nodeX, nodeY, nodeSize, agentStatus[:3], agentStatus[3])
          del agents[nodeId]
        else:
          #agentStatus = [u'Неизвестно']
          #agent = Item(self, nodeId, nodeX, nodeY, nodeSize, agentStatus, colors['offline'])
          agent = Item(self, nodeId, nodeX, nodeY, nodeSize, [], 3)
      if agents.keys() != 0:
        self.createNewAgents(agents)
    else:
      self.createNewAgents(agents)
    self.loadBP()
    self.loadLinks()

  def createNewAgents(self, agents):
    for nodeId, status in agents.items():
      nodeX = 0
      nodeY = 0
      nodeSize = 30
      agent = Item(self, nodeId, nodeX, nodeY, nodeSize, status[:3], status[3])
      agent.moveToCenter()
      schemeDbApi.createNode(nodeId, agent.x(), agent.y(), agent.w)

  def loadLinks(self):
    for i in self.scene.items():
      links = schemeDbApi.readLinks(i.name)
      if len(links) > 0:
        i.links = [x for x in self.scene.items() if x.name in links]
    self.drawLinks()

  def keyPressEvent(self, event):
    if event.key() == QtCore.Qt.Key_Shift:
      QtGui.QApplication.instance().restoreOverrideCursor()
      QtGui.QApplication.instance().restoreOverrideCursor()
      self.setDragMode(QtGui.QGraphicsView.ScrollHandDrag)
      self.wasSelected = list(self.scene.selectedItems())
      for i in self.scene.items():
        i.setAcceptHoverEvents(False)
        i.setAcceptedMouseButtons(QtCore.Qt.NoButton)
      for i in self.wasSelected:
        i.setColor(colors['selected'])
    elif event.key() == QtCore.Qt.Key_Question:
      self.showDB()
    elif event.key() == QtCore.Qt.Key_Insert:
      self.addAgent()
    elif event.key() == QtCore.Qt.Key_Delete:
      self.deleteItem()
    elif event.key() == QtCore.Qt.Key_Greater:
      self.scale(1.1, 1.1)
    elif event.key() == QtCore.Qt.Key_Less:
      self.scale(0.9, 0.9)
    elif event.key() == QtCore.Qt.Key_Equal:
      self.zoomToFit()
    elif event.key() == QtCore.Qt.Key_Plus:
      self.agentSizePlus()
    elif event.key() == QtCore.Qt.Key_Minus:
      self.agentSizeMinus()
    elif event.key() == QtCore.Qt.Key_Asterisk:
      self.addLink()
    elif event.key() == QtCore.Qt.Key_Slash:
      self.removeLink()
    elif event.key() == QtCore.Qt.Key_T:
      for i in self.scene.selectedItems():
        if i.type == 'agent':
          if i.textLocation == 'down':
            i.textLocation = 'up'
            i.update()
          elif i.textLocation == 'up':
            i.textLocation = 'down'
            i.update()
    QtGui.QGraphicsView.keyPressEvent(self, event)

  def keyReleaseEvent(self, event):
    if event.key() == QtCore.Qt.Key_Shift:
      self.setDragMode(QtGui.QGraphicsView.RubberBandDrag)
      for i in self.scene.items():
        i.setAcceptHoverEvents(True)
        i.setAcceptedMouseButtons(QtCore.Qt.LeftButton)
        if i in self.wasSelected:
          i.setSelected(True)
    QtGui.QGraphicsView.keyReleaseEvent(self, event)

  def zoomToFit(self):
    rect = self.scene.itemsBoundingRect()
    rect.setWidth(rect.width()+100)
    rect.setHeight(rect.height()+100)
    rect.setLeft(rect.left()-50)
    rect.setTop(rect.top()-50)
    self.scene.setSceneRect(rect)
    self.fitInView(self.scene.sceneRect(), QtCore.Qt.KeepAspectRatio)

  def selChanged(self):
    for i in self.scene.items():
      if i.type == 'agent' or i.type == 'bp':
        i.setColor()

  def wheelEvent(self, event):
    adj = (event.delta()/120) * 0.1
    self.scale(1+adj, 1+adj)

  def addAgent(self):
    agentId = u"Агент узла {}".format(random.randint(1000, 1000000))
    agentScales = []
    #agent = Item(self, agentId, 0, 0, 30, agentScales, colors['offline'])
    agent = Item(self, agentId, 0, 0, 30, agentScales, 3)
    agent.moveToCenter()
    schemeDbApi.createNode(agentId, agent.x(), agent.y(), agent.w)

  def addLink(self):
    for i in self.scene.selectedItems():
      if i.type == 'agent':
        for agent in self.scene.selectedItems():
          if agent.type == 'agent':
            if agent != i:
              if agent not in i.links and i not in agent.links:
                bpsList = schemeDbApi.readAllBPInLink(i.name, agent.name)
                if len(bpsList) == 0:
                  i.links.append(agent)
                  schemeDbApi.createLink(i.name, agent.name)
    self.drawLinks()

  def removeLink(self):
    if len(self.scene.selectedItems()) == 1 and self.scene.selectedItems()[0].type == 'agent':
      bpsList = schemeDbApi.readAllBPbyNode(self.scene.selectedItems()[0].name)
      if bpsList:
        for bps in bpsList:
          for bp in bps:
            self.removeNode(bp)
      schemeDbApi.deleteLinks(self.scene.selectedItems()[0].name)
    else:
      for i in self.scene.selectedItems():
        if i.type == 'agent':
          for agent in self.scene.selectedItems():
            if agent.type == 'agent':
              if agent in i.links:
                schemeDbApi.deleteLink(i.name, agent.name)
              else:
                bpsList = schemeDbApi.readAllBPInLink(i.name, agent.name)
                for bps in bpsList:
                  for bp in bps:
                    self.removeNode(bp)
    self.parent.mainTable.refresh()

  def drawLinks(self):
    allAgents = []
    for i in self.scene.items():
      if i.type == 'agent' or i.type == 'bp':
        i.lines = []
        allAgents.append(i)
      elif i.type == 'line':
        self.scene.removeItem(i)
    for agent in allAgents:
      for link in agent.links:
        line = Line(agent, link, self)
        agent.lines.append(line)
        link.lines.append(line)
        self.scene.addItem(line)

  def agentSizePlus(self):
    for i in self.scene.selectedItems():
      if i.w < 100 and i.type == 'agent':
        rect = i.boundingRect()
        i.w = rect.width()+5
        i.h = rect.height()+5
        i.lineFollow()
        schemeDbApi.updateNode(i.name, i.x(), i.y(), i.w)
    self.scene.update()

  def agentSizeMinus(self):
    for i in self.scene.selectedItems():
      if i.w > 20 and i.type == 'agent':
        rect = i.boundingRect()
        i.w = rect.width()-5
        i.h = rect.height()-5
        i.lineFollow()
        schemeDbApi.updateNode(i.name, i.x(), i.y(), i.w)
    self.scene.update()

class Table(QtGui.QTableWidget):
  def __init__(self, parent=None):
    super(Table, self).__init__()
    self.parent = parent
    self.bold = QtGui.QFont()
    self.bold.setBold(True)
    self.setAlternatingRowColors(True)
    self.setSortingEnabled(True)
    #self.sortItems(1, QtCore.Qt.DescendingOrder)
    self.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
    self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
    self.customContextMenuRequested.connect(self.openMenu)
    self.verticalHeader().setVisible(False)
    self.setEditTriggers(QtGui.QAbstractItemView.NoEditTriggers)
    self.setColumnCount(5)
    self.setHorizontalHeaderLabels([u'Наименование', u'Начало', u'Конец', u'Длительность', u'Расположение'])
    self.setColumnHidden(4, True)
    #self.cellPressed.connect(lambda: self.parent.mainTableBarCheck.setChecked(False))
    # actions
    self.addAct = QtGui.QAction(QtGui.QIcon(':/icons/icons/Create.png'), u"&Создать шкалу (Insert)",
        self, statusTip=u"Создать шкалу времени", triggered=self.addScale)
    self.startAct = QtGui.QAction(QtGui.QIcon(':/icons/icons/Play.png'), u"&Старт (Space)",
        self, statusTip=u"Начать отчет времени", triggered=lambda: self.startScale())
    self.stopAct = QtGui.QAction(QtGui.QIcon(':/icons/icons/Stop.png'), u"&Стоп (Space)",
        self, statusTip=u"Остановить отчет времени", triggered=lambda: self.stopScale())
    self.delAct = QtGui.QAction(QtGui.QIcon(':/icons/icons/Delete.png'), u"&Удалить (Del)",
        self, statusTip=u"Удалить шкалу", triggered=self.delScales)
    self.refreshAct = QtGui.QAction(QtGui.QIcon(':/icons/icons/Refresh.png'), u"&Обновить (F5)",
        self, statusTip=u"Обновить шкалы", triggered=self.refresh)
    self.setSizePolicy(QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Minimum)

  def keyPressEvent(self, event):
    if event.key() == QtCore.Qt.Key_Delete:
      self.delScales()
    elif event.key() == QtCore.Qt.Key_Space:
      if len(self.selectedItems()) > 0:
        self.stopScale(False)
        self.startScale()
    elif event.key() == QtCore.Qt.Key_F5:
      self.refresh()
    elif event.key() == QtCore.Qt.Key_Insert:
      self.addScale()
    QtGui.QTableWidget.keyPressEvent(self, event)

  def filter(self):
    filterIndex = self.parent.mainTableBarCombo.currentIndex()
    data = API.getScalesLocal()
    #pprint(data)
    if filterIndex == 0:
      return data
    else:
      filteredData = {}
      if data:
        for k, v in data.items():
          filteredData[k] = []
          for scale in v:
            if scale[3] == filterIndex-1:
              filteredData[k].append(scale)
      return filteredData

  def delScales(self):
    reply = QtGui.QMessageBox.question(self, u'Внимание!',
        u'Вы уверены, что хотите удалить выбранные шкалы навсегда?', QtGui.QMessageBox.Yes, QtGui.QMessageBox.No)
    if reply == QtGui.QMessageBox.Yes:
      for i in self.selectedItems():
        if i.column() == 0:
          if not API.deleteScale(str(i.text())):
            QtGui.QMessageBox.warning(
              self, u'Ошибка', u'Шкала {} уже удалена другим агентом шкал.'.format(str(i.text())))
      self.refresh()

  def addScale(self):
    ok, name = NewDialog(u'Введите наименование новой шкалы...', self).getName()
    if ok:
      added = API.createScale(name)
      if not added:
        QtGui.QMessageBox.warning(
          self, u'Ошибка', u'Это наименование шкалы уже использовано.')
      self.refresh()

  def refresh(self):
    self.setRowCount(0)
    scales = self.filter()
    for node, scales in scales.items():
      for i in scales:
        self.loadData(i, node)
    self.parent.searchTable.search()
    self.parent.scheme.loadScheme()

  def getSelected(self):
    d = {}
    for i in self.selectedItems():
      try:
        #d[i.row()].append(str(i.data(0).toString()))
        d[i.row()].append(str(i.text()))
      except KeyError, e:
        #d[i.row()] = [str(i.data(0).toString())]
        d[i.row()] = [str(i.text())]
    for i in self.selectedItems():
      if i.column() == 0:
        #d[i.row()].insert(len(d[i.row()]), i.status)
        d[i.row()].append(i.status)
    return d

  def actRefresh(self):
    d = self.getSelected()
    if d:
      self.startAct.setEnabled(False)
      self.stopAct.setEnabled(False)
      self.delAct.setEnabled(True)
      for k, v in d.items():
        if v[-1] == 0:
          self.startAct.setEnabled(True)
        elif v[-1] == 1:
          self.stopAct.setEnabled(True)
    else:
      self.startAct.setEnabled(False)
      self.stopAct.setEnabled(False)
      self.delAct.setEnabled(False)

  def openMenu(self, position):
    menu = QtGui.QMenu()
    menu.aboutToShow.connect(self.actRefresh)
    menu.addAction(self.refreshAct)
    menu.addSeparator()
    menu.addAction(self.startAct)
    menu.addAction(self.stopAct)
    menu.addSeparator()
    menu.addAction(self.addAct)
    menu.addSeparator()
    menu.addAction(self.delAct)
    menu.exec_(self.viewport().mapToGlobal(position))

  def loadData(self, data, location):
    self.insertRow(0)
    self.setSortingEnabled(False)
    item1 = QtGui.QTableWidgetItem(data[0].decode('utf8'))
    item1.setFont(self.bold)
    item1.status = data[3]
    if data[3] == 0:
      item1.setIcon(QtGui.QIcon(':/icons/icons/dot_grey.png'))
      self.setItem(0, 0, item1)
    elif data[3] == 1:
      item1.setIcon(QtGui.QIcon(':/icons/icons/dot_green.png'))
      self.setItem(0, 0, item1)
      item2 = QtGui.QTableWidgetItem(data[1].strftime("%Y-%m-%d %H:%M:%S"))
      self.setItem(0, 1, item2)
      item4 = DurationWidget(data[1])
      item4.setFont(self.bold)
      self.setItem(0, 3, item4)
    elif data[3] == 2:
      item1.setIcon(QtGui.QIcon(':/icons/icons/dot_red.png'))
      self.setItem(0, 0, item1)
      item2 = QtGui.QTableWidgetItem(data[1].strftime("%Y-%m-%d %H:%M:%S"))
      self.setItem(0, 1, item2)
      item3 = QtGui.QTableWidgetItem(data[2].strftime("%Y-%m-%d %H:%M:%S"))
      self.setItem(0, 2, item3)
      timeDelta = data[2] - data[1]
      item4 = QtGui.QTableWidgetItem(str(timeDelta))
      item4.setFont(self.bold)
      self.setItem(0, 3, item4)
    item5 = QtGui.QTableWidgetItem(location.decode('utf8'))
    self.setItem(0, 4, item5)
    self.setSortingEnabled(True)
    self.resizeColumnsToContents()

  def sort(self):
    self.sortItems(1, QtCore.Qt.DescendingOrder)

  def startScale(self, refr=True):
    d = self.getSelected()
    for k, v in d.items():
      if v[-1] == 0:
        if not API.startScale(v[0]):
          QtGui.QMessageBox.warning(
            self, u'Ошибка', u'Шкала {} уже запущена другим агентом шкал.'.format(v[0]))
    if refr:
      self.refresh()

  def stopScale(self, refr=True):
    d = self.getSelected()
    for k, v in d.items():
      if v[-1] == 1:
        if not API.stopScale(v[0]):
          QtGui.QMessageBox.warning(
            self, u'Ошибка', u'Шкала {} уже остановлена другим агентом шкал.'.format(v[0]))
    if refr:
      self.refresh()

class SearchTable(Table):
  def __init__(self, parent=None):
    super(SearchTable, self).__init__(parent)
    self.setColumnHidden(4, False)

  def refresh(self):
    self.parent.mainTable.refresh()

  def search(self):
    self.setRowCount(0)
    searchName = unicode(self.parent.searchTableBarLine.text())
    found = False
    if searchName != '':
      if searchName == '*':
        found = API.getScales()
      else:
        found = API.searchScale(searchName)
    if found:
      for node, scales in found.items():
        for i in scales:
          self.loadData(i, node)

  #def actRefresh(self):
  #  self.addAct.setEnabled(False)
  #  super(SearchTable, self).actRefresh()

  def openMenu(self, position):
    menu = QtGui.QMenu()
    menu.aboutToShow.connect(self.actRefresh)
    menu.addAction(self.refreshAct)
    menu.addSeparator()
    menu.addAction(self.startAct)
    menu.addAction(self.stopAct)
    menu.addSeparator()
    menu.addAction(self.delAct)
    menu.exec_(self.viewport().mapToGlobal(position))

class DateTime(QtGui.QDateTimeEdit):
  def __init__(self, dateTime, parent=None):
    super(DateTime, self).__init__()
    self.parent = parent
    #self.setCalendarPopup(True)
    #self.calendarWidget().setFirstDayOfWeek(QtCore.Qt.Monday)
    self.setReadOnly(True)
    #print type(dateTime)
    self.setDateTime(QtCore.QDateTime(dateTime))

class ComboBox(QtGui.QComboBox):
  def __init__(self, values, tip, conn, parent=None):
    super(ComboBox, self).__init__()
    self.parent = parent
    self.setToolTip(tip)
    #self.blockSignals(True)
    self.addItems(values)
    #self.setCurrentIndex(values[0])
    #self.blockSignals(False)
    self.currentIndexChanged.connect(conn)

class PushButton(QtGui.QPushButton):
  def __init__(self, icon, tip, conn, parent=None):
    super(PushButton, self).__init__()
    self.setIcon(QtGui.QIcon(icon))
    self.setToolTip(tip)
    self.clicked.connect(conn)

class NewDialog(QtGui.QDialog):
  def __init__(self, title, parent=None):
    super(NewDialog, self).__init__()
    self.parent = parent
    self.setWindowTitle(title)
    self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
    self.setWindowIcon(QtGui.QIcon(':/icons/icons/scales_logo.png'))
    self.setMinimumSize(300, 0)
    self.setMaximumSize(500, 0)
    self.buttons = QtGui.QDialogButtonBox(
      QtGui.QDialogButtonBox.Ok | QtGui.QDialogButtonBox.Cancel,
      QtCore.Qt.Horizontal, self)
    self.buttons.accepted.connect(self.accept)
    self.buttons.rejected.connect(self.reject)
    self.layout = QtGui.QVBoxLayout(self)
    self.layout2 = QtGui.QHBoxLayout()

  def getName(self):
    line = QtGui.QLineEdit()
    _validator = QtGui.QRegExpValidator(reg_ex, line)
    line.setValidator(_validator)
    self.layout2.addWidget(line)
    self.layout.addLayout(self.layout2)
    self.layout.addWidget(self.buttons)
    line.setFocus()
    result = self.exec_()
    return (result == QtGui.QDialog.Accepted,
            unicode(line.text()),
            )

class DurationWidget(QtGui.QTableWidgetItem):
  def __init__(self, start, parent=None):
    super(DurationWidget, self).__init__()
    self.parent = parent
    self.start = start
    self.timer = Timer(0.1, self.calculate)

  def calculate(self):
    processTime = datetime.now() - self.start
    self.setText(str(processTime)[:-3])

class MainWindow(QtGui.QMainWindow):
  def __init__(self):
    super(MainWindow, self).__init__()

    self.setWindowIcon(QtGui.QIcon(':/icons/icons/scales_logo.png'))
    self.setWindowTitle(u'ПК "Ведение шкал ЕОВ"')

    self.status = 0

    # main acts
    self.exitAct = QtGui.QAction(
        QtGui.QIcon(':/icons/icons/Exit.png'), u"Выход",
        self,
        shortcut=QtGui.QKeySequence.Quit,
        statusTip=u"Закрыть программу",
        triggered=QtGui.qApp.closeAllWindows)
    self.okStatusAct = QtGui.QAction(
        QtGui.QIcon(':/icons/icons/status0.png'), u"&Действующий",
        self,
        statusTip=u"Действующий статус локального агента шкал.",
        triggered=self.okStatus)
    self.degradationAct = QtGui.QAction(
        QtGui.QIcon(':/icons/icons/status1.png'), u"&Деградация",
        self,
        statusTip=u"Деградация локального агента шкал.",
        triggered=self.degradation)
    self.fullDegradationAct = QtGui.QAction(
        QtGui.QIcon(':/icons/icons/status2.png'), u"&Критическая деградация",
        self,
        statusTip=u"Критическая деградация локального агента шкал. Локальные шкалы будут скопированы на действующие узлы всязи и удалены.",
        triggered=self.fullDegradation)
    self.deathReactionAct = QtGui.QAction(
        QtGui.QIcon(':/icons/icons/Save.png'), u"&Реакция на аварию в сети",
        self,
        statusTip=u"Запуски реакции на смерть или обрыв связи узла в сети. Сохранение локальных шкал на других узлах, если копий меньше 2.",
        triggered=lambda: API.agentListCheck())
    self.aboutAct = QtGui.QAction(
        QtGui.QIcon(':/icons/icons/Info.png'), u"&О программе",
        self,
        statusTip=u"Открыть описание программы.",
        triggered=self.about)

    # creating scheme widgets
    self.scheme = Scheme(self)

    self.schemeBarBatton1 = PushButton(':/icons/icons/add2.png', u'<b>Создать агента узла (Insert)</b>', self.scheme.addAgent)
    self.schemeBarBatton2 = PushButton(':/icons/icons/link.png', u'<b>Создать связи (*)</b>', self.scheme.addLink)
    self.schemeBarBatton3 = PushButton(':/icons/icons/unlink.png', u'<b>Удалить связи (/)</b>', self.scheme.removeLink)
    self.schemeBarBatton4 = PushButton(':/icons/icons/fit2.png', u'<b>По размеру окна (=)</b>', self.scheme.zoomToFit)
    self.schemeBarBatton5 = PushButton(':/icons/icons/plus.png', u'<b>Увеличить размер агента (+)</b>', self.scheme.agentSizePlus)
    self.schemeBarBatton6 = PushButton(':/icons/icons/minus.png', u'<b>Уменьшить размер агента (-)</b>', self.scheme.agentSizeMinus)
    self.schemeBarBatton7 = PushButton(':/icons/icons/Delete.png', u'<b>Удаление неактивного агента (Delete)</b>', self.scheme.deleteItem)
    schemeBar = QtGui.QHBoxLayout()
    schemeBar.addStretch(1)
    #schemeBar.addWidget(self.schemeBarBatton1)
    #schemeBar.addSpacing(20)
    #schemeBar.addWidget(self.schemeBarBatton6)
    #schemeBar.addWidget(self.schemeBarBatton5)
    #schemeBar.addSpacing(20)
    schemeBar.addWidget(self.schemeBarBatton2)
    schemeBar.addWidget(self.schemeBarBatton3)
    #schemeBar.addSpacing(20)
    #schemeBar.addWidget(self.schemeBarBatton7)
    schemeBar.addSpacing(20)
    schemeBar.addWidget(self.schemeBarBatton4)
    schemeBar.addStretch(1)

    schemeBox = QtGui.QVBoxLayout()
    schemeBox.addLayout(schemeBar)
    schemeBox.addWidget(self.scheme)

    schemeWidget = QtGui.QWidget()
    schemeWidget.setLayout(schemeBox)


    # creating main table widgets
    self.mainTable = Table(self)
    # auto refresh timer
    self.timer = Timer(0, self.mainTable.refresh)

    self.mainTableBarLab1 = QtGui.QLabel(u"Автообновление:")
    self.mainTableBarLab2 = QtGui.QLabel(u"Фильтр:")
    self.mainTableBarCheck = QtGui.QCheckBox()
    self.mainTableBarCheck.setToolTip(u'<b>Включение/выключение автообновления</b>')
    self.mainTableBarCheck.stateChanged.connect(self.autoUpdateOnOff)
    self.mainTableBarSpin = QtGui.QSpinBox()
    #self.mainTableBarSpin.setPrefix(u' ')
    self.mainTableBarSpin.setSuffix(u' с')
    self.mainTableBarSpin.setMinimum(1)
    self.mainTableBarSpin.setToolTip(u'<b>Период автообновления</b>')
    self.mainTableBarSpin.valueChanged.connect(self.autoUpdateInterval)
    self.mainTableBarSpin.setValue(10)
    #self.mainTableBarBatton1 = PushButton(':/icons/icons/Refresh.png', u'<b>Обновить</b>', self.mainTable.refresh)
    self.mainTableBarBatton2 = PushButton(':/icons/icons/Create.png', u'<b>Загеристрировать новую шкалу</b>', self.mainTable.addScale)
    self.mainTableBarCombo = ComboBox([u'Все', u'Зарегистрированные', u'Текущие', u'Завершенные'],
                                      u'<b>Фильтр шкал по статусу</b>',
                                      self.mainTable.refresh)
    mainTableBar = QtGui.QHBoxLayout()
    #mainTableBar.addWidget(self.mainTableBarBatton2)
    #mainTableBar.addSpacing(20)
    mainTableBar.addWidget(self.mainTableBarLab1)
    mainTableBar.addWidget(self.mainTableBarCheck)
    mainTableBar.addWidget(self.mainTableBarSpin)
    #mainTableBar.addWidget(self.mainTableBarBatton1)
    mainTableBar.addSpacing(200)
    mainTableBar.addStretch(1)
    mainTableBar.addWidget(self.mainTableBarLab2)
    mainTableBar.addWidget(self.mainTableBarCombo)

    mainTableBox = QtGui.QVBoxLayout()
    mainTableBox.addLayout(mainTableBar)
    mainTableBox.addWidget(self.mainTable)

    mainTableWidget = QtGui.QWidget()
    mainTableWidget.setLayout(mainTableBox)

    # creating search table widgets
    self.searchTable = SearchTable(self)

    #self.searchTableBarLab = QtGui.QLabel(u"Поиск по всем доступным агентам шкал")
    self.searchTableBarLine = QtGui.QLineEdit()
    self.searchTableBarLine.setPlaceholderText(u'Поиск шкал по всем доступным агентам')
    self.searchTableBarLine.returnPressed.connect(self.searchTable.refresh)
    _validator = QtGui.QRegExpValidator(reg_ex, self.searchTableBarLine)
    self.searchTableBarLine.setValidator(_validator)

    self.searchTableBarBatton1 = PushButton(':/icons/icons/View.png', u'<b>Поиск</b>', self.searchTable.refresh)
    searchTableBar = QtGui.QHBoxLayout()
    #searchTableBar.addWidget(self.searchTableBarLab)
    #searchTableBar.addSpacing(20)
    searchTableBar.addWidget(self.searchTableBarLine)
    searchTableBar.addWidget(self.searchTableBarBatton1)
    #searchTableBar.addStretch(1)

    searchTableBox = QtGui.QVBoxLayout()
    searchTableBox.addLayout(searchTableBar)
    searchTableBox.addWidget(self.searchTable)

    searchTableWidget = QtGui.QWidget()
    searchTableWidget.setLayout(searchTableBox)

    # adding scheme and main tree widgets to splitter
    self.subSplitter = QtGui.QSplitter()
    self.subSplitter.setOrientation(QtCore.Qt.Vertical)
    self.subSplitter.addWidget(mainTableWidget)
    self.subSplitter.addWidget(searchTableWidget)
    self.subSplitter.setSizes([300,100])

    # adding scheme and main tree widgets to splitter
    self.splitter = QtGui.QSplitter()
    self.splitter.addWidget(self.subSplitter)
    self.splitter.addWidget(schemeWidget)
    self.splitter.setSizes([1,2000])

    self.setCentralWidget(self.splitter)

    self.createMenus()
    self.createStatusBar()

    self.readSettings()

    #self.ping()

    self.mainTable.refresh()
    self.mainTable.sort()
    self.scheme.zoomToFit()

  def createMenus(self):
    self.fileMenu = self.menuBar().addMenu(u"&Файл")
    self.fileMenu.addAction(self.mainTable.addAct)
    self.fileMenu.addSeparator()
    self.fileMenu.addAction(self.exitAct)
    #self.fileMenu.aboutToShow.connect(self.updateFileMenu)
    self.settingsMenu = self.menuBar().addMenu(u"&Статус")
    self.settingsMenu.addAction(self.deathReactionAct)
    self.settingsMenu.addSeparator()
    self.settingsMenu.addAction(self.okStatusAct)
    self.settingsMenu.addAction(self.degradationAct)
    self.settingsMenu.addAction(self.fullDegradationAct)
    self.helpMenu = self.menuBar().addMenu(u"&Помощь")
    self.helpMenu.addAction(self.aboutAct)

  def about(self):
    QtGui.QMessageBox.about(self, u'О программе',
        u'ПК "Ведение шкал единого оперативного времени"')

  def createStatusBar(self):
    self.diod = QtGui.QLabel()
    self.diod.setPixmap(QtGui.QPixmap(self.statusIcon()))
    self.statusBar().addPermanentWidget(self.diod)

  def updateStatusIcon(self):
    self.statusBar().removeWidget(self.diod)
    self.diod = QtGui.QLabel()
    self.diod.setPixmap(QtGui.QPixmap(self.statusIcon()))
    self.statusBar().addPermanentWidget(self.diod)

  def statusIcon(self):
    #self.status = API.getDegradeStatus()
    return ':/icons/icons/status{}.png'.format(self.status)

  def okStatus(self):
    self.status = 0
    print u'Ok Status - {}'.format(self.status)
    API.setDegradeStatus(self.status)
    self.updateStatusIcon()

  def degradation(self):
    self.status = 1
    print u'Degradation status - {}'.format(self.status)
    API.setDegradeStatus(self.status)
    self.updateStatusIcon()

  def fullDegradation(self):
    self.status = 2
    print u'Full degradation status - {}'.format(self.status)
    API.setDegradeStatus(self.status)
    self.updateStatusIcon()

  def otherDegradation(self):
    ok, IP = NewDialog(u'Введите IP адрес агента шкал...', self).getName()
    if ok:
      print u'Sudden death of an scales agent, ip: {}'.format(IP)
      API.dieWithoutPermittion(IP)

  def autoUpdateOnOff(self, state):
    if state:
      self.timer.start()
    else:
      self.timer.stop()

  def autoUpdateInterval(self, value):
    self.timer.setInterval(value*1000)

  def closeEvent(self, event):
    self.writeSettings()
    event.accept()

  def readSettings(self):
    settings = QtCore.QSettings('Rubin', 'Scales')
    if settings.value('size').toString() == 'max':
      self.showMaximized()
    else:
      self.move(settings.value('pos').toPoint())
      self.resize(settings.value('size').toSize())

  def writeSettings(self):
    settings = QtCore.QSettings('Rubin', 'Scales')
    if self.isMaximized():
      settings.setValue('size', 'max')
    else:
      settings.setValue('pos', self.pos())
      settings.setValue('size', self.size())

  def ping(self):
    print API.connCheck()

class Timer(QtCore.QTimer):
  def __init__(self, interval, func, parent=None):
    super(Timer, self).__init__()
    self.parent = parent
    self.setInterval(interval*1000)
    self.timeout.connect(func)
    if interval:
      self.start()

if __name__ == '__main__':
  app = QtGui.QApplication(sys.argv)
  mainWin = MainWindow()
  mainWin.show()
  sys.exit(app.exec_())
