//
//  StemThickness.m
//  StemThickness
//
//  Created by Georg Seifert on 20.03.21.
//Copyright © 2021 RafalBuchner. All rights reserved.
//

#import "StemThickness.h"
#import <GlyphsCore/GlyphsFilterProtocol.h>
#import <GlyphsCore/GSGlyphEditViewProtocol.h>
#import <GlyphsCore/GSFilterPlugin.h>
#import <GlyphsCore/GSGlyph.h>
#import <GlyphsCore/GSLayer.h>
#import <GlyphsCore/GSFont.h>
#import <GlyphsCore/GSPath.h>
#import <GlyphsCore/GSFontMaster.h>
#import <GlyphsCore/GSComponent.h>
#import <GlyphsCore/GSProxyShapes.h>
#import <GlyphsCore/GSCallbackHandler.h>
#import <GlyphsCore/NSString+BadgeDrawing.h>
#import <GlyphsCore/GSWindowControllerProtocol.h>
#import <GlyphsCore/GSGeometrieHelper.h>
#import <vector>
#import <algorithm>

@interface GSWindowController: NSWindowController<GSWindowControllerProtocol>
@property NSArray *toolInstances;
@end

@interface GSDocument: NSDocument
- (GSFontMaster*)selectedFontMaster;
- (GSWindowController *) windowController;
@end

NSPoint GSMiddlePointStem(NSPoint a, NSPoint b) {
	a.x = (a.x + b.x) * 0.5;
	a.y = (a.y + b.y) * 0.5;
	return a;
}

NSString *formatDistance(CGFloat d, CGFloat scale) {
	// calculates how value of thickness will be shown
	if (scale < 2) {
		return [NSString stringWithFormat:@"%d", (int)round(d)];
		// return "%i." % round(d) // use this instead if you really want the dot at the end, but I don't understand why --mekkablue
	}
	else if (scale < 3) {
		return [NSString stringWithFormat:@"%0.1f", d];
	}
	else if (scale < 10) {
		return [NSString stringWithFormat:@"%0.2f", d];
	}
	return [NSString stringWithFormat:@"%0.3f", d];
}

static NSColor *red = nil;
static NSColor *blue = nil;
static NSColor *pointColor = nil;

@implementation StemThickness {
	GSFont *_font;
	GSFontMaster *_master;
	NSViewController <GSGlyphEditViewControllerProtocol> *_editViewController;
	CGFloat _scale;
	NSPoint _layerOrigin;
	NSUInteger _textCursorPosition;
	NSArray *_allLayers;
}

+ (void)initialize {
	static dispatch_once_t onceToken;
	dispatch_once(&onceToken, ^{
		red  = [NSColor colorWithCalibratedRed:0.96 green:0.44 blue:0.44 alpha:1];
		blue = [NSColor colorWithCalibratedRed:0.65 green:0.63 blue:0.94 alpha:1];
		pointColor = [NSColor colorWithCalibratedRed:0.2 green:0.6 blue:0.6 alpha:0.7];
	});
}

- (instancetype)init {
	self = [super init];
	if (self) {
		// do stuff
	}
	return self;
}

- (NSUInteger)interfaceVersion {
	// Distinguishes the API verison the plugin was built for. Return 1.
	return 1;
}

- (NSString *)title {
	return NSLocalizedStringFromTableInBundle(@"Stem Thickness", nil, [NSBundle bundleForClass:[self class]], @"");
}

- (NSString *)keyEquivalent {
	return @"s";
}

- (NSEventModifierFlags)modifierMask {
	return NSEventModifierFlagControl;
}

- (void)drawForegroundWithOptions:(NSDictionary *)options {
	NSView <GSGlyphEditViewProtocol> *view = _editViewController.graphicView;
	_scale = view.scale; // scale of edit window
	GSFont *font = [_editViewController representedObject];
	CGFloat upm = font.unitsPerEm;
	if (_scale < 0.15 * 1000 / upm || _scale > 6.0 * 1000 / upm) {
		return;
	}
	NSPoint crossHairCenter = [view getActiveLocation:[NSApp currentEvent]];
	_layerOrigin = view.activePosition;

	GSLayer *layer = [[view activeLayer] copyDecomposedLayer];
	NSDictionary *closestData = [self calcClosestInfo:layer position:crossHairCenter];
	if (!closestData) {
		return;
	}
	GSLog(@"closestData %@", closestData);
	if (GSDistance(crossHairCenter, [closestData[@"onCurve"] pointValue]) > 35 / _scale) {
		_lastNodePair = nil;
		return;
	}
	[self drawCrossingsForData:closestData];
}

- (CGFloat)getHandleSize {
	/*
	 Returns the current handle size as set in user preferences.
	 */
	NSUInteger selected = [NSUserDefaults.standardUserDefaults integerForKey:@"GSHandleSize"];
	if (selected == 0) {
		return 5.0;
	}
	else if (selected == 2) {
		return 10.0;
	}
	else {
		return 7.0;  // Regular
	}
}

- (void)drawPoint:(NSPoint)thisPoint size:(CGFloat)size color:(NSColor *)color {
	if (!color) {
		color = pointColor;
	}
	// from Show Angled Handles by MekkaBlue
	[color set];
	NSRect myRect = NSMakeRect(thisPoint.x - size * 0.5, thisPoint.y - size * 0.5, size, size);
	NSBezierPath *seledinCircles = [NSBezierPath bezierPathWithOvalInRect:myRect];
	[seledinCircles fill];
}

- (void)drawDashedStrokeA:(NSPoint)a b:(NSPoint)b {
	NSBezierPath *bez = [NSBezierPath bezierPath];
	bez.lineWidth = 0;
	CGFloat dash[] = {2.0, 2.0};
	[bez setLineDash:dash count:2 phase:0];
	[bez moveToPoint:a];
	[bez lineToPoint:b];
	[bez stroke];
}

+(CGFloat)distanceSquared:(NSPoint)p1 to:(NSPoint)p2 {
	return (p1.x-p2.x)*(p1.x-p2.x) + (p1.y-p2.y)*(p1.y-p2.y);
}

+(NSPoint)setLongerCoordinate:(NSPoint)v toLength:(CGFloat)length {
	if (fabs(v.x) > fabs(v.y)) {
		v.y *= length / v.x;
		v.x = length;
	}
	else {
		v.x *= length / v.y;
		v.y = length;
	}
	return v;
}

// returns the two points closest to referencePoint
+(NSArray *)closestPointsTo:(NSPoint)referencePoint inPoints:(NSArray *)points {
	if (points.count <= 1) return points;
	NSPoint prevPoint = [points.firstObject pointValue];
	CGFloat toFirstSquared = [StemThickness distanceSquared:prevPoint to:referencePoint];
	CGFloat prevSquared = toFirstSquared;
	for (int i = 1; i != points.count; ++i) {
		NSPoint point = [points[i] pointValue];
		CGFloat distanceSquared = [StemThickness distanceSquared:point to:referencePoint];
		CGFloat betweenSquared = [StemThickness distanceSquared:point to:prevPoint];
		if (betweenSquared > distanceSquared + prevSquared) {
			return [points subarrayWithRange:NSMakeRange(i-1, 2)];
		}
		prevSquared = distanceSquared;
		prevPoint = point;
	}
	// must be outside the points.
	NSUInteger loc = (toFirstSquared < prevSquared) ? 0 : (points.count - 2);
	// ^ keep in mind that prevDistanceSquared is the distance to the last point
	return [points subarrayWithRange:NSMakeRange(loc, 2)]; // the first or last two points
}

- (void)drawCrossingsForPoints:(NSArray *)crossPoints {
	NSPoint p0 = [crossPoints[0] pointValue];
	NSPoint p1 = [crossPoints[1] pointValue];
	CGFloat distance01 = GSDistance(p0, p1);
	[self showDistance:distance01 cross:p0 onCurve:p1 color:blue];
	if (crossPoints.count == 3) {
		NSPoint p2 = [crossPoints[2] pointValue];
		CGFloat distance12 = GSDistance(p2, p1);
		[self showDistance:distance12 cross:p2 onCurve:p1 color:blue];
	}
}

- (void)showDistance:(CGFloat)d cross:(NSPoint)cross onCurve:(NSPoint)onCurve color:(NSColor *)color {
	cross = GSScalePoint(cross, _scale);
	cross = GSAddPoints(cross, _layerOrigin);
	onCurve = GSScalePoint(onCurve, _scale);
	onCurve = GSAddPoints(onCurve, _layerOrigin);
	CGFloat handleSize = [self getHandleSize];
	CGFloat zoomedHandleSize = handleSize * 0.875 * 0.75;
	NSString *distanceShowed = formatDistance(d, _scale);
	NSPoint thisDistanceCenter = GSMiddlePointStem(onCurve, cross);
	[color set];
	[self drawDashedStrokeA:onCurve b:cross];
	CGFloat fontSize = handleSize * 1.5 * pow(_scale, 0.1);
	[distanceShowed drawBadgeAtPoint:thisDistanceCenter size:fontSize color:NSColor.textColor backgroundColor:[color blendedColorWithFraction:0.8 ofColor:NSColor.textBackgroundColor] alignment:GSCenterCenter visibleInRect:NSMakeRect(NSNotFound, 0, 0, 0)];
	[self drawPoint:cross size:zoomedHandleSize color:color];
	[self drawPoint:onCurve size:zoomedHandleSize color:color];
}

- (void)mouseMoved:(NSNotification *)notification {
	[_editViewController redraw];
}

- (void)willActivate {
	[[NSNotificationCenter defaultCenter] addObserver:self selector:@selector(mouseMoved:) name:@"mouseMovedNotification" object:nil];
}

- (void)willDeactivate {
	[[NSNotificationCenter defaultCenter] removeObserver:self];
}


+(NSPoint)closestPointToCursor:(NSPoint)cursor onLayer:(GSLayer *)layer {
	NSPoint closestPoint = NSMakePoint(CGFLOAT_MAX, CGFLOAT_MAX);
	CGFloat closestDistSquared = CGFLOAT_MAX;
	GSLayer * decomposedLayer = [layer copyDecomposedLayer];
	for (GSPath *path in decomposedLayer.paths) {
		CGFloat currPathTime; // just a dummy, result unused
		NSPoint currClosestPoint = [path nearestPointOnPath:cursor pathTime:&currPathTime];
		CGFloat currDistSquared = [StemThickness distanceSquared:cursor to:currClosestPoint];
		if (currDistSquared < closestDistSquared) {
			closestDistSquared = currDistSquared;
			closestPoint = currClosestPoint;
		}
	}
	return closestPoint;
}

+(NSPoint)closestPointToCursorNEW:(NSPoint)cursor onLayer:(GSLayer *)layer {
	GSLayer * decomposedLayer = [layer copyDecomposedLayer];
	std::vector<std::pair<double,std::pair<double, double>>> closestPoints;
	for (GSPath *path in decomposedLayer.paths) {
		for ( int i = 0; i != path.countOfNodes; ++i ) {
			GSNode * p0 = path.nodes[i];
			if ( p0.type == OFFCURVE ) continue;
			GSNode * p1 = path.nodes[(i+1) % path.countOfNodes];
			CGFloat t;
			NSPoint nearestPointInSegment;
			if ( p1.type == OFFCURVE ) {
				GSNode * p2 = path.nodes[(i+2) % path.countOfNodes];
				GSNode * p3 = path.nodes[(i+3) % path.countOfNodes];
				assert( p3 == p0.nextOncurveNode );
				NSPoint p0p = p0.position;
				NSPoint p1p = p1.position;
				NSPoint p2p = p2.position;
				NSPoint p3p = p3.position;
				CGFloat * tp = &t;
				nearestPointInSegment = GSNearestPointOnCurve( cursor, p0p, p1p, p2p, p3p, tp );
			}
			else {
				assert( p1 == p0.nextOncurveNode );
//				nearestPointInSegment = GSNearestPointOnLine( cursor, p0.position, p1.position, &t );
			}
			CGFloat dsq = [StemThickness distanceSquared:cursor to:nearestPointInSegment];
			closestPoints.emplace_back( dsq, std::make_pair( nearestPointInSegment.x, nearestPointInSegment.y ) );
		}
	}
	std::sort( closestPoints.begin(), closestPoints.end() );
	auto nearest = closestPoints.front().second;
	return NSMakePoint( nearest.first, nearest.second );
}

- (NSArray *)intersectionsOnNeighbourLayer:(GSLayer *)layer left:(BOOL)left crossPoints:(NSArray *)crossPoints closestPointNormal:(NSPoint)closestPointNormal minusClosestPointNormal:(NSPoint)minusClosestPointNormal {
	if (left && _textCursorPosition == 0) return crossPoints;
	if (! left && _textCursorPosition == _allLayers.count - 1) return crossPoints;
	assert(_allLayers[_textCursorPosition] == layer);
	GSLayer *neighbour = left ? _allLayers[_textCursorPosition-1] : _allLayers[_textCursorPosition+1];
	CGFloat xOffset = left ? -neighbour.width : layer.width;
	GSGlyph *firstGlyph = left ? neighbour.parent : layer.parent;
	GSGlyph *secondGlyph = left ? layer.parent : neighbour.parent;
	CGFloat kerning = [_font kerningForFontMasterID:_master.id firstGlyph:firstGlyph secondGlyph:secondGlyph direction:GSWritingDirectionLeftToRight];
	if (kerning != LLONG_MAX) {
		// ^ Glyphs returns this funny value if kerning not defined
		xOffset += left ? -kerning : kerning;
	}
	closestPointNormal.x -= xOffset;
	minusClosestPointNormal.x -= xOffset;
	NSArray *crossPointsNeighbour = [neighbour calculateIntersectionsStartPoint:closestPointNormal endPoint:minusClosestPointNormal decompose:YES];
	if (crossPointsNeighbour.count < 2) {
		// no neighbour intersections
		return crossPoints;
	}
	crossPointsNeighbour = [crossPointsNeighbour subarrayWithRange:NSMakeRange(1, crossPointsNeighbour.count - 2)];
	NSMutableArray *temp = left ? [NSMutableArray array] : [crossPoints mutableCopy];
	for (NSValue *v in crossPointsNeighbour) {
		NSPoint point = v.pointValue;
		point.x += xOffset;
		[temp addObject:@(point)];
	}
	if (left) [temp addObjectsFromArray:crossPoints];
	return temp;
}

- (NSArray *)intersectionsOnLayer:(GSLayer *)layer nearMouseCursor:(NSPoint)pt {
	NSPoint closestPoint = [StemThickness closestPointToCursor:pt onLayer:layer];
	if (closestPoint.x == CGFLOAT_MAX) return nil;
	NSPoint direction = [StemThickness setLongerCoordinate:GSSubtractPoints(pt, closestPoint) toLength:_font.unitsPerEm+layer.width];
	NSPoint startPoint = GSAddPoints(pt, direction);
	NSPoint endPoint = GSSubtractPoints(pt, direction);
	NSArray *crossPoints = [layer calculateIntersectionsStartPoint:startPoint endPoint:endPoint decompose:YES];
	// note: the first and last objects in crossPoints are identical to the start and end points (or vice versa)
	if (crossPoints.count <= 2) {
		// no intersections found
		return nil;
	}
	// remove the first and last element:
	crossPoints = [crossPoints subarrayWithRange:NSMakeRange(1, crossPoints.count - 2)];
	
	if (startPoint.x > endPoint.x + 0.001) {
		// not vertical
		CGFloat xLeft = [crossPoints.firstObject pointValue].x;
		CGFloat xRight = [crossPoints.lastObject pointValue].x;
		if (pt.x < xLeft || pt.x > xRight) {
			// outside the crossPoints
			crossPoints = [self intersectionsOnNeighbourLayer:layer left:(pt.x < xLeft) crossPoints:crossPoints closestPointNormal:startPoint minusClosestPointNormal:endPoint];
			// TODO: the point closest to the mouse cursor may be on the neighbouring layer
			// TODO: ideally, the tool could be used to measure between or within far away neighbours,
			//       just like Glyphs’ measurement tool
		}
	}
	return [StemThickness closestPointsTo:pt inPoints:crossPoints];
}

- (NSViewController <GSGlyphEditViewControllerProtocol>*)controller {
	return _editViewController;
}

- (void)setController:(NSViewController <GSGlyphEditViewControllerProtocol>*)Controller {
	// Use [self controller]; as object for the current view controller.
	_editViewController = Controller;
}

@end
