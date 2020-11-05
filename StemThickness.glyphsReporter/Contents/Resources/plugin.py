# encoding: utf-8
from __future__ import division, print_function, unicode_literals

###########################################################################################################
#
#
#	Reporter Plugin
#
#	Read the docs:
#	https://github.com/schriftgestalt/GlyphsSDK/tree/master/Python%20Templates/Reporter
#
#
###########################################################################################################

import objc, math
from GlyphsApp import *
from GlyphsApp.plugins import *
import traceback

red  = NSColor.colorWithCalibratedRed_green_blue_alpha_(0.96, 0.44, 0.44, 1)
blue = NSColor.colorWithCalibratedRed_green_blue_alpha_(0.65, 0.63, 0.94, 1)
pointColor = NSColor.colorWithCalibratedRed_green_blue_alpha_(0.2, 0.6, 0.6, 0.7)
def pathAB(t, Wx, Wy):
	summaX = Wx[0] + t * (Wx[1] - Wx[0])
	summaY = Wy[0] + t * (Wy[1] - Wy[0])
	return NSPoint(summaX, summaY)

def calcTangent(t, segment):
	# calculates reference Tangent Point (from its coordinates plugin will be able to get tangent's direction)
	if len(segment) == 4: # for curves
		divided = divideCurve(segment[0], segment[1], segment[2], segment[3], t)
		R2 = divided[4]
	elif len(segment) == 2: # for line
		R2 = segment[1]
	
	Tangent = NSPoint(R2.x, R2.y)
	return Tangent

def angle(A, B):
	try:
		"""calc angle between AB and Xaxis """
		xDiff = A.x - B.x
		yDiff = A.y - B.y
		if yDiff== 0 or xDiff== 0:
			tangens = 0
		else:
			tangens = yDiff / xDiff
		return math.atan(tangens)
	except:
		print(traceback.format_exc())

def rotatePoint(P, angle, originPoint):
		"""Rotates x/y around x_orig/y_orig by angle and returns result as [x, y]."""
		alfa = math.radians(angle)

		x = (P.x - originPoint.x) * math.cos(alfa) - (P.y - originPoint.y) * math.sin(alfa) + originPoint.x
		y = (P.x - originPoint.x) * math.sin(alfa) + (P.y - originPoint.y) * math.cos(alfa) + originPoint.y

		RotatedPoint = NSPoint(x, y)
		return RotatedPoint

def formatDistance(d, scale):
	# calculates how value of thickness will be shown
	if scale < 2:
		return "%i" % round(d)
		# return "%i." % round(d) # use this instead if you really want the dot at the end, but I don't understand why --mekkablue
	elif scale < 3:
		return "%0.1f" % d
	elif scale < 10:
		return "%0.2f" % d
	elif scale >= 10:
		return "%0.3f" % d

class StemThickness(ReporterPlugin):
	lastNodePair = None
	
	@objc.python_method
	def settings(self):
		self.menuName = Glyphs.localize({
			'en': u'Stem Thickness',
			'de': u'Stammstärke',
			'fr': u'l’épaisseur des traits',
			'es': u'espesor',
			'jp': u'ステムの太さ',
		})
		self.keyboardShortcut = 's'
		self.keyboardShortcutModifier = NSControlKeyMask
		self.controller = None

	@objc.python_method
	def _foreground(self, layer):
		try:
			import cProfile
			cProfile.runctx('self._foreground(layer)', globals(), locals())
			print("**")
		except:
			print(traceback.format_exc())
		
	@objc.python_method
	def foreground(self, layer):
		# Glyphs.clearLog() ### delete!
		view = self.controller.graphicView()
		crossHairCenter = view.getActiveLocation_(Glyphs.currentEvent())
		scale = self.getScale() # scale of edit window

		closestData = self.calcClosestInfo(layer, crossHairCenter)
		if closestData is None:
			return
		if distance(crossHairCenter, closestData['onCurve']) > 35 / scale:
			self.lastNodePair = None
			return

		self.drawCrossingsForData(closestData)

	@objc.python_method
	def drawCrossingsForData(self, closestData):
		HandleSize = self.getHandleSize()
		scale = self.getScale()
		myPointsSize = HandleSize - HandleSize / 8
		zoomedMyPoints = myPointsSize / scale

		layer = closestData["layer"]
		closestPoint = closestData['onCurve']
		self.drawPoint(closestPoint, zoomedMyPoints)
		
		# returns list of intersections
		crossPoints = layer.intersectionsBetweenPoints(closestData['normal'], closestData['minusNormal'])
		
		if len(crossPoints) > 2:
			# find closest point in the list of intersections
			# the point before and after that point is what we are looking for
			closestI = -1
			closestDistance = 1000000
			i = 0
			for cross in crossPoints:
				dist = distance(NSPoint(cross.x, cross.y), closestPoint)
				if dist < closestDistance:
					closestDistance = dist
					closestI = i
				i += 1
			if closestI < 1:
				return
			i = closestI
			n = i - 1
			if i < len(crossPoints):
				i += 1
			try:
				FirstCrossPointA = NSPoint(crossPoints[i].x, crossPoints[i].y)	#blue
				FirstDistance  = distance(closestPoint, FirstCrossPointA)
				FirstCrossPointB = NSPoint(crossPoints[n].x, crossPoints[n].y)	#red
				SecondDistance = distance(closestPoint, FirstCrossPointB)

				firstDraws  = False
				if 0.01 < FirstDistance < 1199:
					firstDraws = True
					self.showDistance(FirstDistance, FirstCrossPointA, closestPoint, blue)
				if 0.01 < SecondDistance < 1199:
					secondColor = blue
					if firstDraws == True:
						secondColor = red
					self.showDistance(SecondDistance, FirstCrossPointB, closestPoint, secondColor)
			except:
				print(traceback.format_exc())

	@objc.python_method
	def showDistance(self, d, cross, onCurve, color):
		self.lastNodePair = (cross, onCurve)
		scale = self.getScale() # scale of edit window
		HandleSize = self.getHandleSize()
		myPointsSize = HandleSize - HandleSize / 8
		zoomedMyPoints = myPointsSize / scale
		distanceShowed = formatDistance(d, scale)
		thisDistanceCenter = pathAB(0.5, (onCurve.x, cross.x), (onCurve.y, cross.y))
		color.set()
		self.drawDashedStrokeAB(onCurve, cross)
		self.drawRoundedRectangleForStringAtPosition(" %s " % distanceShowed, thisDistanceCenter, 8, color=color)
		self.drawPoint(cross, zoomedMyPoints * 0.75, color=color)

	def mouseDidMove_(self, notification):
		if self.controller:
			self.controller.redraw()

	def willActivate(self):
		Glyphs.addCallback(self.mouseDidMove_, MOUSEMOVED)

	def willDeactivate(self):
		try:
			Glyphs.removeCallback(self.mouseDidMove_, MOUSEMOVED)
			self.lastNodePair = None
		except:
			print(traceback.format_exc())

	@objc.python_method
	def drawPoint(self, ThisPoint, scale, color=pointColor):
		"""from Show Angled Handles by MekkaBlue"""
		try:
			color.set()
			seledinCircles = self.roundDotForPoint(ThisPoint, scale)
			seledinCircles.fill()
		except:
			print(traceback.format_exc())

	@objc.python_method
	def roundDotForPoint(self, thisPoint, markerWidth):
		"""
		from Show Angled Handles by MekkaBlue
		Returns a circle with thisRadius around thisPoint.
		"""
		myRect = NSRect((thisPoint.x - markerWidth * 0.5, thisPoint.y - markerWidth * 0.5), (markerWidth, markerWidth))
		return NSBezierPath.bezierPathWithOvalInRect_(myRect)

	@objc.python_method
	def drawDashedStrokeAB(self, A, B):
		bez = NSBezierPath.bezierPath()
		bez.setLineWidth_(0)
		bez.setLineDash_count_phase_((2.0, 2.0), 2, 0)
		bez.moveToPoint_(A)
		bez.lineToPoint_(B)
		bez.stroke()

	@objc.python_method
	def calcClosestInfo(self, layer, pt):
		try:
			closestPoint = None
			closestPath = None
			closestPathTime = None
			dist = 100000
			for path in layer.paths:
				currClosestPoint, currPathTime = path.nearestPointOnPath_pathTime_(pt, None)
				currDist = distance(currClosestPoint, pt)
				if currDist < dist:
					dist = currDist
					closestPoint = currClosestPoint
					closestPathTime = currPathTime
					closestPath = path
			if closestPathTime is None:
				return None
			n = math.floor(closestPathTime)
			OnNode = closestPath.nodes[n]
			if not OnNode:
				return None
			if OnNode.type == CURVE:
				segment = (closestPath.nodes[n - 3].position, closestPath.nodes[n - 2].position, closestPath.nodes[n - 1].position, OnNode.position)
			else:
				prevPoint = closestPath.nodes[n - 1]
				if prevPoint:
					segment = (prevPoint.position, OnNode.position)
				else:
					return None

			TangentDirection = calcTangent(closestPathTime % 1, segment)
			directionAngle = angle(closestPoint, TangentDirection)

			if TangentDirection.x == segment[0].x: # eliminates problem with vertical lines ###UGLY?
				directionAngle = -math.pi / 2

			if directionAngle < 0:
				directionAngle += math.pi # 180 degree

			scale = self.getScale()

			yTanDistance = (10000 / scale) * math.sin(directionAngle)
			xTanDistance = (10000 / scale) * math.cos(directionAngle)
			closestPointTangent = NSPoint(xTanDistance + closestPoint.x, yTanDistance + closestPoint.y)
			closestPointNormal = NSPoint(rotatePoint(closestPointTangent, 90, closestPoint).x, rotatePoint(closestPointTangent, 90, closestPoint).y)

			MINUSyTanDistance = -yTanDistance
			MINUSxTanDistance = -xTanDistance
			MINUSclosestPointTangent = NSPoint(MINUSxTanDistance + closestPoint.x, MINUSyTanDistance + closestPoint.y)
			minusClosestPointNormal = NSPoint(rotatePoint(MINUSclosestPointTangent, 90, closestPoint).x, rotatePoint(MINUSclosestPointTangent, 90, closestPoint).y)

			return {
				"onCurve": closestPoint,
				"normal": closestPointNormal,
				"pathTime": closestPathTime,
				"path": closestPath,
				"segment": segment,
				"minusNormal": minusClosestPointNormal,
				"layer": layer,
			}
		except:
			print(traceback.format_exc())
			return None

	####### From ShowStems by Mark2Mark

	@objc.python_method
	def drawRoundedRectangleForStringAtPosition(self, thisString, center, fontsize, color=(0, .3, .9, .65)):
		''' Thanks to Mekkablue for this one '''
		x, y = center
		scaledSize = fontsize / self.getScale()
		width = len(thisString) * scaledSize * 0.7
		rim = scaledSize * 0.3
		panel = NSRect()
		panel.origin = NSPoint(x-width / 2, y - scaledSize / 2 - rim)
		panel.size = NSSize(width, scaledSize + rim * 2)
		NSColor.textBackgroundColor().set()
		roundedRect = NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(panel, scaledSize * 0.5, scaledSize * 0.5)
		roundedRect.fill()
		NSColor.textColor().set()
		roundedRect.setLineWidth_(0.1 / self.getScale())
		roundedRect.stroke()
		self.drawTextAtPoint(thisString, center, fontsize, fontColor = NSColor.textColor(), align=“center”)

	@objc.python_method
	def conditionalContextMenus(self):
		contextMenus = []
		if not self.lastNodePair is None:
			contextMenus.append({
					'name': Glyphs.localize({
						'en': u'Add Measurement Guide',
						'de': u'Messlinie hinzufügen',
						'fr': u'Ajouter un guide de dimension',
						'es': u'Añadir guía con medidas',
						'jp': u'計測ガイドを追加',
					}),
					'action': self.addGuideForMeasurement,
				})
		return contextMenus

	@objc.python_method
	def addGuideForMeasurement(self):
		try:
			currentLayer = Glyphs.font.selectedLayers[0]
			node1 = self.lastNodePair[0]
			node2 = self.lastNodePair[1]
			guideKnobPosition = NSPoint(
				(node1.x+node2.x) * 0.5,
				(node1.y+node2.y) * 0.5,
			)
			guideAngle = angle(node1, node2)
			newGuide = GSGuideLine()
			newGuide.position = guideKnobPosition
			newGuide.angle = math.degrees(guideAngle)
			newGuide.setShowMeasurement_(True)
			currentLayer.guides.append(newGuide)
			
			# make sure Show Guides is enabled:
			Glyphs.defaults["showGuidelines"] = 1
		except:
			print(traceback.format_exc())

	@objc.python_method
	def __file__(self):
		"""Please leave this method unchanged"""
		return __file__
