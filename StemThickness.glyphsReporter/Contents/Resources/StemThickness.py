# encoding: utf-8

###########################################################################################################
#
#
#   Reporter Plugin
#
#   Read the docs:
#   https://github.com/schriftgestalt/GlyphsSDK/tree/master/Python%20Templates/Reporter
#
#
###########################################################################################################

from GlyphsApp.plugins import *
from GlyphsApp import MOUSEMOVED
import traceback, objc, itertools, math

def pathAB(t,Wx,Wy):
    summaX = Wx[0] + t*(Wx[1] - Wx[0])
    summaY = Wy[0] + t*(Wy[1] - Wy[0])

    T = NSPoint(summaX,summaY)
    return T

def calcTangent(t,segment):
    # calculates reference Tangent Point (from its coordinates plugin will be able to get tangent's direction)
    if len(segment) == 4: # for curves
        divided = divideCurve(segment[0], segment[1], segment[2], segment[3], t)
        R2 = divided[4]
    elif len(segment) == 2: # for line
        R2 = segment[1]
    
    Tangent = NSPoint(R2.x,R2.y)
    return Tangent

def angle( A, B ):
    try:
        """calc angle between AB and Xaxis """
        xDiff = A.x - B.x
        yDiff = A.y - B.y
        if yDiff== 0 or xDiff== 0:
            tangens = 0
        else:
            tangens = yDiff / xDiff

        angle = math.atan( tangens )
        return angle
    except:
        print(traceback.format_exc())

def rotatePoint( P,angle, originPoint):

        """Rotates x/y around x_orig/y_orig by angle and returns result as [x,y]."""
        alfa = math.radians(angle)

        x = ( P.x - originPoint.x ) * math.cos( alfa ) - ( P.y - originPoint.y ) * math.sin( alfa ) + originPoint.x
        y = ( P.x - originPoint.x ) * math.sin( alfa ) + ( P.y - originPoint.y ) * math.cos( alfa ) + originPoint.y

        RotatedPoint = NSPoint(x,y)
        return RotatedPoint

def formatDistance(d, scale):
    # calculates how value of thickness will be shown
    dot = ""
    roundedDistance = 0
    if scale < 2:
        roundedDistance = int(round(d))
        dot = "."
    elif scale < 3:
        roundedDistance = round(d, 1)
    elif scale < 10:
        roundedDistance = round(d, 2)
    elif scale >= 10:
        roundedDistance = round(d, 3)
    return str(roundedDistance) + dot

class StemThickness(ReporterPlugin):

    def settings(self):
        self.menuName = 'Stem Thickness'

        self.keyboardShortcut = 'a'
        self.keyboardShortcutModifier = NSCommandKeyMask | NSShiftKeyMask | NSAlternateKeyMask

    def _foreground(self, layer):
        try:
            import cProfile
            cProfile.runctx('self._foreground(layer)', globals(), locals())
            print "**"
        except:
            print traceback.format_exc()
        
    def foreground(self, layer):
        # Glyphs.clearLog() ### delete!
        view = self.controller.graphicView()
        crossHairCenter = view.getActiveLocation_(Glyphs.currentEvent())
        scale = self.getScale() # scale of edit window
        layer = Glyphs.font.selectedLayers[0]

        #r eturns closest point on curve to crossHairCenter
        resultPoints = self.calcClosestPtOnCurveAndTangent(layer, crossHairCenter,scale)
        # print "resultPoints", resultPoints
        # then point on curve (only in certian distance)
        HandleSize = self.getHandleSize()
        myPointsSize = HandleSize - HandleSize / 8
        zoomedMyPoints = myPointsSize / scale

        if distance(crossHairCenter,resultPoints['onCurve']) <= 35/scale:

            self.drawPoint(resultPoints['onCurve'], zoomedMyPoints)
            # returns list of intersections
            crossPoints = layer.intersectionsBetweenPoints( resultPoints['onCurve'],resultPoints['normal'])
            MINUScrossPoints = layer.intersectionsBetweenPoints( resultPoints['onCurve'],resultPoints['minusNormal'])
            segment = self.getCurrSegment(layer,crossHairCenter)

            if len(segment) == 4: # curves
                MINUScrossPoints.reverse()
                i = -2
                n = -2
            else: # lines
                allCurrPoints_x = []
                allCurrPoints_y = []
                for path in layer.paths:
                    for node in path.nodes:
                        allCurrPoints_x.append(node.x)
                        allCurrPoints_y.append(node.y)

                if segment[0].y == segment[1].y and segment[0].y != min(allCurrPoints_y) and segment[0].y != max(allCurrPoints_y): # FOR LINES THAT ARE HORIZONTAL
                    crossPoints.reverse()
                    del crossPoints[-1]
                    del MINUScrossPoints[-1]
                    i = -2
                    n = -2
                elif segment[0].y == segment[1].y and segment[0].y == min(allCurrPoints_y): # FOR LINES THAT ARE HORIZONTAL and stays at the lowest level
                    # print "LOW LEVEL"
                    MINUScrossPoints.reverse()
                    crossPoints.reverse()
                    del crossPoints[-1]
                    i = -2
                    n = 1 
                elif segment[0].y == segment[1].y and segment[0].y == max(allCurrPoints_y): # FOR LINES THAT ARE HORIZONTAL and stays at the highest level
                    # print "HIGHT LEVEL"
                    MINUScrossPoints.reverse()
                    crossPoints.reverse()
                    del crossPoints[-1]
                    del MINUScrossPoints[-1]
                    i = 0
                    n = 2
                elif segment[0].x == max(allCurrPoints_x) and segment[1].x == max(allCurrPoints_x): # for lines extreme right vertival lines
                    # print "RIGHT LEVEL"
                    crossPoints.reverse()
                    i = 2
                    n = 1

                elif segment[0].x == segment[1].x and segment[1].x == min(allCurrPoints_x): # for lines extreme left vertival lines
                    # print "LEFT LEVEL"
                    i = 0
                    n = 2

                elif segment[0].x != segment[1].x and segment[0].y != segment[1].y: 
                    # print "DIAGONAl"
                    del crossPoints[-1]
                    i = -2
                    n = 2

                elif segment[0].x == segment[1].x and segment[1].x != min(allCurrPoints_x) or segment[1].x != max(allCurrPoints_x):
                    # print "STRAIGHT"
                    del crossPoints[-1]
                    i = -2
                    n = 2

            FirstCrossPointA = NSPoint(crossPoints[i].x,crossPoints[i].y)           #blue
            FirstCrossPointB = NSPoint(MINUScrossPoints[n].x,MINUScrossPoints[n].y) #red

            # drawsLine between points on curve
            NSBezierPath.setDefaultLineWidth_( 1.0 / scale )
            fontColor = NSColor.whiteColor()

            FirstDistance = distance( resultPoints['onCurve'], FirstCrossPointA )

            firstDraws  = False
            red  =  (0.96, 0.44, 0.44, 1)
            blue = ( 0.65, 0.63, 0.94, 1 )
            dot = ""
            if FirstDistance < 1199:
                # sets colors
                firstDraws = True
                self.showDistance(FirstDistance, FirstCrossPointA, resultPoints['onCurve'], blue)
            SecondDistance = distance( resultPoints['onCurve'], FirstCrossPointB )
            if SecondDistance < 1199:
                secondColor = blue
                if firstDraws == True:
                    secondColor = red
                self.showDistance(SecondDistance, FirstCrossPointB, resultPoints['onCurve'], secondColor)

            if FirstCrossPointA == resultPoints['onCurve'] or FirstCrossPointA == resultPoints['onCurve']:
                print "ERROR: crossPoint == ON CURVE POINT!!!!"

    def showDistance(self, d, cross, onCurve, color):
        scale = self.getScale() # scale of edit window
        HandleSize = self.getHandleSize()
        myPointsSize = HandleSize - HandleSize / 8
        zoomedMyPoints = myPointsSize / scale
        distanceShowed = formatDistance(d,scale)
        thisDistanceCenter = pathAB(0.5, [onCurve.x, cross.x],[onCurve.y, cross.y] )
        NSColor.colorWithCalibratedRed_green_blue_alpha_( *color ).set()
        self.drawDashedStrokeAB( onCurve, cross )
        self.drawRoundedRectangleForStringAtPosition(" %s " % distanceShowed, (thisDistanceCenter.x, thisDistanceCenter.y), 8, color = color)
        self.drawPoint(cross, zoomedMyPoints*0.75, color = color)

    def mouseDidMove(self, notification):
        self.controller.view().setNeedsDisplay_(True)

    def willActivate(self):
        Glyphs.addCallback(self.mouseDidMove, MOUSEMOVED)

    def willDeactivate(self):
        try:
            Glyphs.removeCallback(self.mouseDidMove, MOUSEMOVED)
        except:
            NSLog(traceback.format_exc())

    def drawPoint(self, ThisPoint, scale, color = ( 0.2, 0.6, 0.6, 0.7 )):
        """from Show Angled Handles by MekkaBlue"""
        try:
            NSColor.colorWithCalibratedRed_green_blue_alpha_( *color ).set()
            seledinCircles = NSBezierPath.alloc().init()
            seledinCircles.appendBezierPath_( self.roundDotForPoint( ThisPoint, scale ) )
            seledinCircles.fill()
        except:
            print(traceback.format_exc())

    def roundDotForPoint( self, thisPoint, markerWidth ):
        """
        from Show Angled Handles by MekkaBlue
        Returns a circle with thisRadius around thisPoint.
        """
        myRect = NSRect( ( thisPoint.x - markerWidth * 0.5, thisPoint.y - markerWidth * 0.5 ), ( markerWidth, markerWidth ) )
        return NSBezierPath.bezierPathWithOvalInRect_(myRect)
    def drawDashedStrokeAB(self,A,B):
        bez = NSBezierPath.bezierPath()
        bez.setLineWidth_(0)
        bez.setLineDash_count_phase_([2.0,2.0], 2,0)
        bez.moveToPoint_(A)
        bez.lineToPoint_(B)
        bez.stroke()
    def calcClosestPtOnCurveAndTangent(self, layer, crossHairCenter, scale):
        try:
            closestPoint = None
            closestPath = None
            closestPathTime = None
            dist = 100000
            for path in layer.paths:
                currClosestPoint, currPathTime = path.nearestPointOnPath_pathTime_(crossHairCenter, None)
                #print "currClosestPoint, crossHairCenter", currClosestPoint, currPathTime
                currDist = distance(currClosestPoint, crossHairCenter)
                if currDist < dist:
                    dist = currDist
                    closestPoint = currClosestPoint
                    closestPathTime = currPathTime
                    closestPath = path
            n = math.floor(closestPathTime)
            OnNode = closestPath.nodes[n]
            if OnNode.type == CURVE:
                segment = (closestPath.nodes[n - 3].position, closestPath.nodes[n - 2].position, closestPath.nodes[n - 1].position, OnNode.position)
            else:
                segment = (closestPath.nodes[n - 1].position, OnNode.position)
            TangentDirection = calcTangent(closestPathTime % 1, segment)
            diractionAngle = angle(closestPoint,TangentDirection)

            if TangentDirection.x == segment[0].x : # eliminates problem with vertical lines ###UGLY?
                diractionAngle = -math.pi/2

            if diractionAngle < 0:
                diractionAngle += math.pi # 180 degree

            yTanDistance = (10000/scale) * math.sin(diractionAngle)
            xTanDistance = (10000/scale) * math.cos(diractionAngle)
            closestPointTangent = NSPoint(xTanDistance+closestPoint.x,yTanDistance+closestPoint.y)
            closestPointNormal = NSPoint(rotatePoint(closestPointTangent, 90, closestPoint).x,rotatePoint(closestPointTangent, 90, closestPoint).y)   

            MINUSyTanDistance = -yTanDistance
            MINUSxTanDistance = -xTanDistance
            MINUSclosestPointTangent = NSPoint(MINUSxTanDistance+closestPoint.x,MINUSyTanDistance+closestPoint.y)
            minusClosestPointNormal = NSPoint(rotatePoint(MINUSclosestPointTangent, 90, closestPoint).x,rotatePoint(MINUSclosestPointTangent, 90, closestPoint).y)  

            dictOfclosestAndTangent = {'onCurve': closestPoint,'normal': closestPointNormal,'minusNormal': minusClosestPointNormal}
            return dictOfclosestAndTangent
        except:
            print traceback.format_exc()

    ####### From ShowStems by Mark2Mark

    def drawRoundedRectangleForStringAtPosition(self, thisString, center, fontsize, color=(0, .3, .8, .65) ):
        ''' Thanks to Mekkablue for this one '''
        x, y = center
        scaledSize = fontsize / self.getScale()
        width = len(thisString) * scaledSize * 0.7
        rim = scaledSize * 0.3
        panel = NSRect()
        panel.origin = NSPoint( x-width/2, y-scaledSize/2-rim )
        panel.size = NSSize( width, scaledSize + rim*2 )
        NSColor.colorWithCalibratedRed_green_blue_alpha_( 1,1,1,1 ).set()
        # NSColor.colorWithCalibratedRed_green_blue_alpha_( *color ).set() # ORGINAL
        NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_( panel, scaledSize*0.5, scaledSize*0.5 ).fill()
        NSColor.colorWithCalibratedRed_green_blue_alpha_( 0,0,0,0.1 ).set()
        NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_( panel, scaledSize*0.5, scaledSize*0.5 ).stroke()
        self.drawTextAtPoint(thisString, center, fontsize )
    def drawTextAtPoint(self, text, textPosition, fontSize=10.0, fontColor=NSColor.blackColor(), align='center'):
        """
        custom drawTextAtPoint() by Mark.
        """
        try:
            
            alignment = {
                'topleft': 6, 
                'topcenter': 7, 
                'topright': 8,
                'left': 3, 
                'center': 4, 
                'right': 5, 
                'bottomleft': 0, 
                'bottomcenter': 1, 
                'bottomright': 2
                }
            
            glyphEditView = self.controller.graphicView()
            currentZoom = self.getScale()
            fontAttributes = { 
                NSFontAttributeName: NSFont.labelFontOfSize_(fontSize/currentZoom),

                # NSForegroundColorAttributeName: NSColor.colorWithCalibratedRed_green_blue_alpha_( 1, 1, 1, 1 ), # fontColor, original
                NSForegroundColorAttributeName: NSColor.colorWithCalibratedRed_green_blue_alpha_( 0,0,0,1 ), # fontColor,
                # NSBackgroundColorAttributeName: NSColor.colorWithCalibratedRed_green_blue_alpha_( 0, .3, .8, .65 ),
                }
            displayText = NSAttributedString.alloc().initWithString_attributes_(text, fontAttributes)
            textAlignment = alignment[align] # top left: 6, top center: 7, top right: 8, center left: 3, center center: 4, center right: 5, bottom left: 0, bottom center: 1, bottom right: 2
            glyphEditView.drawText_atPoint_alignment_(displayText, textPosition, textAlignment)
        except:
            self.logError(traceback.format_exc())

    def getCurrSegment(self,layer,crossHairCenter):
        """Thanks to Georg"""
        try:
            closestPath = None
            closestPathTime = None
            dist = 100000
            for path in layer.paths:
                currClosestPoint, currPathTime = path.nearestPointOnPath_pathTime_(crossHairCenter, None)
                #print "currClosestPoint, crossHairCenter", currClosestPoint, currPathTime
                currDist = distance(currClosestPoint, crossHairCenter)
                if currDist < dist:
                    dist = currDist  
                    closestPathTime = currPathTime
                    closestPath = path
            n = math.floor(closestPathTime)
            OnNode = closestPath.nodes[n]
            if OnNode.type == CURVE:
                segment = (closestPath.nodes[n - 3].position, closestPath.nodes[n - 2].position, closestPath.nodes[n - 1].position, OnNode.position)
            else:
                segment = (closestPath.nodes[n - 1].position, OnNode.position)
            return segment
        except:
            print traceback.format_exc()