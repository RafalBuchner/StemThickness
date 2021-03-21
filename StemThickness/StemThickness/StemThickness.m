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
	NSViewController <GSGlyphEditViewControllerProtocol> *_editViewController;
	id _lastNodePair;
	CGFloat _scale;
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

- (void)drawForegroundForLayer:(GSLayer *)layer options:(NSDictionary *)options {
//- (void)drawForegroundWithOptions:(NSDictionary *)options {
	NSView <GSGlyphEditViewProtocol> *view = _editViewController.graphicView;
	NSPoint crossHairCenter = [view getActiveLocation:[NSApp currentEvent]];
	_scale = view.scale; // scale of edit window
	//GSLayer *layer = [view activeLayer];
	NSDictionary *closestData = [self calcClosestInfo:layer position:crossHairCenter];
	if (!closestData) {
		return;
	}
	if (GSDistance(crossHairCenter, [closestData[@"onCurve"] pointValue]) > 35 / _scale) {
		_lastNodePair = nil;
		return;
	}
	[self drawCrossingsForData:closestData];
}

- (CGFloat)getHandleSize {
	/*
	Returns the current handle size as set in user preferences.
	Use: self.getHandleSize() / self.getScale()
	to determine the right size for drawing on the canvas.
	 */
	NSUInteger Selected = [NSUserDefaults.standardUserDefaults integerForKey:@"GSHandleSize"];
	if (Selected == 0) {
		return 5.0;
	}
	else if (Selected == 2) {
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
	@try {
		[color set];
		NSRect myRect = NSMakeRect(thisPoint.x - size * 0.5, thisPoint.y - size * 0.5, size, size);
		NSBezierPath *seledinCircles = [NSBezierPath bezierPathWithOvalInRect:myRect];
		[seledinCircles fill];
	}
	@catch (NSException *exception) {
		NSLog(@"__drawPoint %@", exception);
	}
}

- (void)drawDashedStrokeA:(NSPoint)A b:(NSPoint)B {
	NSBezierPath *bez = [NSBezierPath bezierPath];
	bez.lineWidth = 0;
	CGFloat dash[] = {2.0, 2.0};
	[bez setLineDash:dash count:2 phase:0];
	[bez moveToPoint:A];
	[bez lineToPoint:B];
	[bez stroke];
}

- (void)drawCrossingsForData:(NSDictionary *)closestData {
	CGFloat HandleSize = [self getHandleSize];

	CGFloat zoomedHandleSize = HandleSize * 0.875 / _scale;

	GSLayer *layer = closestData[@"layer"];
	NSPoint closestPoint = [closestData[@"onCurve"] pointValue];
	[self drawPoint:closestPoint size:zoomedHandleSize color:nil];

	// returns list of intersections
	NSArray *crossPoints = [layer calculateIntersectionsStartPoint:[closestData[@"normal"] pointValue] endPoint:[closestData[@"minusNormal"] pointValue] decompose:NO];

	if (crossPoints.count > 2) {
		// find closest point in the list of intersections
		// the point before and after that point is what we are looking for
		NSInteger closestI = -1;
		CGFloat closestDistance = 1000000;
		NSInteger i = 0;
		for (NSValue *crossValue in crossPoints) {
			NSPoint cross = [crossValue pointValue];
			CGFloat dist = GSDistance(cross, closestPoint);
			if (dist < closestDistance) {
				closestDistance = dist;
				closestI = i;
			}
			i++;
		}
		if (closestI < 1) {
			return;
		}
		i = closestI;
		NSInteger n = i - 1;
		if (i < crossPoints.count) {
			i++;
		}
		@try {
			NSPoint FirstCrossPointA = [crossPoints[i] pointValue];	// blue
			CGFloat FirstDistance  = GSDistance(closestPoint, FirstCrossPointA);
			NSPoint FirstCrossPointB = [crossPoints[n] pointValue];	// red
			CGFloat SecondDistance = GSDistance(closestPoint, FirstCrossPointB);

			BOOL firstDraws = NO;
			if (0.01 < FirstDistance && FirstDistance < 1199) {
				firstDraws = YES;
				[self showDistance:FirstDistance cross:FirstCrossPointA onCurve:closestPoint color:blue];
			}
			if (0.01 < SecondDistance && SecondDistance < 1199) {
				NSColor *secondColor = firstDraws ? red : blue;
				[self showDistance:SecondDistance cross:FirstCrossPointB onCurve:closestPoint color:secondColor];
			}
		}
		@catch (NSException *exception) {
			NSLog(@"!!drawCrossingsForData %@", exception);
		}
	}
}

- (void)showDistance:(CGFloat)d cross:(NSPoint)cross onCurve:(NSPoint)onCurve color:(NSColor *)color {
	// self.lastNodePair = (cross, onCurve) //TODO

	CGFloat handleSize = [self getHandleSize];
	CGFloat zoomedHandleSize = handleSize * 0.875 * 0.75 / _scale;
	NSString *distanceShowed = formatDistance(d, _scale);
	NSPoint thisDistanceCenter = GSMiddlePointLine(onCurve, cross);
	[color set];
	[self drawDashedStrokeA:onCurve b:cross];
	[distanceShowed drawBadgeAtPoint:thisDistanceCenter size:8 / _scale color:NSColor.textBackgroundColor backgroundColor:color alignment:GSCenterCenter visibleInRect:NSMakeRect(NSNotFound, 0, 0, 0)];
	[self drawPoint:cross size:zoomedHandleSize color:color];
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

- (NSDictionary *)calcClosestInfo:(GSLayer *)layer position:(NSPoint)pt {
	@try {
		NSPoint closestPoint = NSZeroPoint;
		CGFloat dist = 100000.0;
		for (GSPath *path in layer.paths) {
			CGFloat currPathTime;
			NSPoint currClosestPoint = [path nearestPointOnPath:pt pathTime:&currPathTime];
			CGFloat currDist = GSDistance(currClosestPoint, pt);
			if (currDist < dist) {
				dist = currDist;
				closestPoint = currClosestPoint;
			}
		}
		if (dist > 99999.0) {
			return nil;
		}
		NSPoint direction = GSUnitVectorFromTo(pt, closestPoint);
		NSPoint closestPointNormal = GSAddPoints(pt, GSScalePoint(direction, 10000));
		NSPoint minusClosestPointNormal = GSAddPoints(pt, GSScalePoint(direction, -10000));
		return @{
			@"onCurve": @(closestPoint),
			@"normal": @(closestPointNormal),
			@"minusNormal": @(minusClosestPointNormal),
			@"layer": layer,
		};
	}
	@catch (NSException *exception) {
		NSLog(@"__calcClosestInfo: %@", exception);
	}
	return nil;
}

- (void)drawBackgroundForLayer:(GSLayer*)layer options:(NSDictionary *)options {}

- (void)drawBackgroundForInactiveLayer:(GSLayer*)layer options:(NSDictionary *)options {}

- (void)setController:(NSViewController <GSGlyphEditViewControllerProtocol>*)Controller {
	// Use [self controller]; as object for the current view controller.
	_editViewController = Controller;
}

@end
