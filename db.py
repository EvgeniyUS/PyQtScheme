# -*- coding: utf-8 -*-

import sqlite3
from sqlite3 import Error

def create_connection(db_file):
  try:
    conn = sqlite3.connect(db_file)
    conn.text_factory = str
    return conn
  except Error, e:
    print e
    return False

class DataBase():
  def __init__(self, connect):
    if connect:
      self.conn = connect
      self.cursor = self.conn.cursor()
      self.createNodeTable()
      #self.dropTable()
      self.createLinkTable()
  def createNodeTable(self):
    try:
      query = '''CREATE TABLE IF NOT EXISTS "node" (
                  id varchar(150) PRIMARY KEY,
                  x real,
                  y real,
                  size real
                  );'''
      self.cursor.execute(query)
      self.conn.commit()
    except Error, e:
      print e
  def dropTable(self):
    try:
      query = '''DROP TABLE links'''
      self.cursor.execute(query)
      self.conn.commit()
    except Error, e:
      print e
  def createLinkTable(self):
    try:
      query = '''CREATE TABLE IF NOT EXISTS "links" (
                  node varchar(150),
                  link varchar(150),
                  PRIMARY KEY (node, link)
                  );'''
                  #id INTEGER PRIMARY KEY,
      self.cursor.execute(query)
      self.conn.commit()
    except Error, e:
      print e
  def createLink(self, nodeId, linkId):
    try:
      query = '''INSERT INTO links("node", "link") values (?, ?)'''
      self.cursor.execute(query, (nodeId, linkId, ))
      self.conn.commit()
      return True
    except Error, e:
      print e
      self.conn.rollback()
      return False
  def readLink(self, nodeId, linkId):
    try:
      query = '''SELECT node, link from links WHERE (node = (?) AND link = (?)) OR (node = (?) AND link = (?))'''
      self.cursor.execute(query, (nodeId, linkId, linkId, nodeId))
      data = self.cursor.fetchone()
      if data:
        return data
      else:
        return False
    except Error, e:
      print e
      return False
  def readLinks2(self, nodeId):
    try:
      query1 = '''SELECT node from links WHERE link = (?)'''
      query2 = '''SELECT link from links WHERE node = (?)'''
      self.cursor.execute(query1, (nodeId, ))
      data = self.cursor.fetchall()
      List = []
      for i in data:
        List.append(i[0])
      self.cursor.execute(query2, (nodeId, ))
      data = self.cursor.fetchall()
      for i in data:
        List.append(i[0])
      return List
    except Error, e:
      print e
      return False
  def readLinks(self, nodeId):
    try:
      query = '''SELECT link from links WHERE node = (?)'''
      self.cursor.execute(query, (nodeId, ))
      data = self.cursor.fetchall()
      List = []
      for i in data:
        List.append(i[0])
      return List
    except Error, e:
      print e
      return False
  def readAllLinks(self):
    try:
      query = '''SELECT * from links'''
      self.cursor.execute(query)
      data = self.cursor.fetchall()
      return data
    except Error, e:
      print e
      return False
  def deleteLink(self, nodeId, linkId):
    try:
      query = '''DELETE FROM links WHERE node = (?) AND link = (?)'''
      self.cursor.execute(query, (nodeId, linkId))
      self.cursor.execute(query, (linkId, nodeId))
      self.conn.commit()
      return True
    except Error, e:
      print e
      self.conn.rollback()
      return False
  def deleteLinks(self, nodeId):
    try:
      query = '''DELETE FROM links WHERE node = (?) OR link = (?)'''
      self.cursor.execute(query, (nodeId, nodeId))
      self.conn.commit()
      return True
    except Error, e:
      print e
      self.conn.rollback()
      return False
  def updateLink(self, nodeId, linkId, bpId):
    try:
      query = '''UPDATE links SET link = (?) WHERE (node = (?) AND link = (?)) OR (node = (?) AND link = (?))'''
      self.cursor.execute(query, (bpId, nodeId, linkId, linkId, nodeId))
      self.conn.commit()
      return True
    except Error, e:
      print e
      self.conn.rollback()
      return False
  def readBP(self):
    try:
      #query = '''SELECT * from node WHERE size < 20'''
      query = '''SELECT * from node WHERE id LIKE 'breakingPoint%' '''
      self.cursor.execute(query)
      data = self.cursor.fetchall()
      return data
    except Error, e:
      print e
      return False
  def readAllBPInLink(self, node1, node2):
    try:
      query = '''SELECT id from node WHERE id LIKE 'breakingPoint%' || (?) || '%' || (?) || '%' '''
      self.cursor.execute(query, (node1, node2))
      data = self.cursor.fetchall()
      if not data:
        self.cursor.execute(query, (node2, node1))
        data = self.cursor.fetchall()
      return data
    except Error, e:
      print e
      return False
  def readAllBPbyNode(self, node):
    try:
      #query = '''SELECT id from node WHERE (id LIKE 'breakingPoint##' || (?) || '%') OR
      #                                     (id LIKE 'breakingPoint##%##' || (?) || '%')'''
      query = '''SELECT id from node WHERE id LIKE 'breakingPoint%' || (?) || '%' '''
      self.cursor.execute(query, (node, ))
      data = self.cursor.fetchall()
      return data
    except Error, e:
      print e
      return False
  def readNodes(self):
    try:
      query = '''SELECT * from node WHERE size >= 20'''
      self.cursor.execute(query)
      data = self.cursor.fetchall()
      return data
    except Error, e:
      print e
      return False
  def createNode(self, nodeId, nodeX, nodeY, nodeSize):
    try:
      query = '''INSERT INTO node("id", "x", "y", "size") values (?, ?, ?, ?)'''
      self.cursor.execute(query, (nodeId, nodeX, nodeY, nodeSize, ))
      self.conn.commit()
      return True
    except Error, e:
      print e
      self.conn.rollback()
      return False
  def updateNode(self, nodeId, nodeX, nodeY, nodeSize):
    try:
      query = '''UPDATE node SET x = (?), y = (?), size = (?) WHERE id = (?)'''
      self.cursor.execute(query, (nodeX, nodeY, nodeSize, nodeId))
      self.conn.commit()
      return True
    except Error, e:
      print e
      self.conn.rollback()
      return False
  def deleteNode(self, nodeId):
    try:
      query = '''DELETE FROM node WHERE id = (?)'''
      self.cursor.execute(query, (nodeId, ))
      self.conn.commit()
      return True
    except Error, e:
      print e
      self.conn.rollback()
      return False
  def deleteAll(self):
    try:
      query = ''' DELETE FROM node'''
      self.cursor.execute(query)
      self.conn.commit()
      return True
    except Error, e:
      print e
      self.conn.rollback()
      return False

if __name__ == '__main__':
  dbApi = DataBase(create_connection('scales.db'))
  #dbApi.createNode("1", 0, 0, 30)
  #print dbApi.readData()
  #dbApi.updateNode("1", 1, 1, 40)
  #print dbApi.readData()
  #dbApi.deleteNode("1")
  #print dbApi.readData()
  #print "------"
  #print dbApi.readAllLinks()
  dbApi.dropTable()

