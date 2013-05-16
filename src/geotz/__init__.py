__all__ = ['get_tz']

import pickle
import os
import sys
import csv
import unittest
from warnings import warn

from shapely.wkt import loads
from shapely.prepared import prep


# timeZones.txt came from http://download.geonames.org/
tzdata = csv.reader(file(os.path.join(os.path.dirname(__file__), 'timeZones.txt')), delimiter = '\t')
tzdata.next()
tzdict = dict([(n, dict(jan = float(g), jul = float(d), gmt = float(r))) for n,g,d,r in tzdata])

# Define data for longitude-based timezones
# no daylight savings time, so just one offset value
lon_bounds = [[-172.5, -157.5, -11.],
              [-157.5, -142.5, -10.],
              [-142.5, -127.5,  -9.],
              [-127.5, -112.5,  -8.],
              [-112.5,  -97.5,  -7],
              [ -97.5,  -82.5,  -6],
              [ -82.5,  -67.5,  -5],
              [ -67.5,  -52.5,  -4],
              [ -52.5,  -37.5,  -3],
              [ -37.5,  -22.5,  -2],
              [ -22.5,   -7.5,  -1],
              [  -7.5,    7.5,   0],
              [   7.5,   22.5,   1],
              [  22.5,   37.5,   2],
              [  37.5,   52.5,   3],
              [  52.5,   67.5,   4],
              [  67.5,   82.5,   5],
              [  82.5,   97.5,   6],
              [  97.5,  112.5,   7],
              [ 112.5,  127.5,   8],
              [ 127.5,  142.5,   9],
              [ 142.5,  157.5,  10],
              [ 157.5,  172.5,  11],
              [ 172.5,  180. ,  12],
              [ 180. ,  187.5, -12.],
              [-180. , -172.5, -12.]] 

uspklpath = os.path.join(os.path.dirname(__file__),'USTimeZones.pkl')
worldpklpath = os.path.join(os.path.dirname(__file__),'WorldTimeZones.pkl')

def makepkl():
    """
    makepkl creates a pickle file from a kml file to improve run time.
    """
    # Old osgeo.ogr approach
    from osgeo import ogr
    # USTimeZones.kml source is unknown, but was freely available and
    # Has been converted to a pkl file
    kmlpath = os.path.join(os.path.dirname(__file__), 'USTimeZones.kml')
    driver = ogr.GetDriverByName('KML')
    datasource = driver.Open(kmlpath)
    layer = datasource.GetLayer()
    layerDefn = layer.GetLayerDefn()
    oldfeats = [i_ for i_ in layer]
    featDefn = layer.GetLayerDefn()
    feat = ogr.Feature(featDefn)
    nbFeat = layer.GetFeatureCount()
    outfeat = file(uspklpath, 'w')
    featout = [(feat.GetField(0), feat.GetGeometryRef().ExportToWkt()) for feat in oldfeats]
    pickle.dump(featout, file(uspklpath, 'w'))

    # WorldTimeZones.kml source is below and was freely available and
    # Has been converted to a pkl file
    # https://productforums.google.com/forum/?fromgroups=#!msg/gec-tools/EdR18tz_5k8/MRPV85OxXIkJ
    kmlpath = os.path.join(os.path.dirname(__file__), 'WorldTimeZones.kml')
    driver = ogr.GetDriverByName('KML')
    datasource = driver.Open(kmlpath)
    layer = datasource.GetLayer()
    layerDefn = layer.GetLayerDefn()
    oldfeats = [i_ for i_ in layer]
    featDefn = layer.GetLayerDefn()
    feat = ogr.Feature(featDefn)
    nbFeat = layer.GetFeatureCount()
    outfeat = file(worldpklpath, 'w')
    featout = [(feat.GetField(0), feat.GetGeometryRef().ExportToWkt()) for feat in oldfeats]
    pickle.dump(featout, file(worldpklpath, 'w'))

if not os.path.exists(uspklpath) or not os.path.exists(worldpklpath):
    print "Creating pkl file"
    makepkl()

# Load shape definitions as a list of tuples 
# that define timezones using Well Known Text (WKT)
# polygons
#
# [(tzname, Polygon definition), ...]
usfeatsdict = pickle.load(file(uspklpath))
worldfeatsdict = pickle.load(file(worldpklpath))

# Convert WKT to shapely prepared shapes
# Preparing shapes improve repeated use, but
# slows import time
usfeats = [(k, prep(loads(v))) for k, v in usfeatsdict if v is not None]
worldfeats = [(k, prep(loads(v))) for k, v in worldfeatsdict if v is not None]



def get_tz(lon, lat):
    """
    Takes longitude and latitude and returns a string identifying
    the source of timezone information and a dictionary with 
    a time offset to get offset on January 1 (2012) (jan; aka Local Daylight
    Time northern hemisphere), offset on July 1 (2012) (jul, aka Local Standard
    Time (lst), or offset from Greenwich Mean Time (gmt) ignoring Daylight
    savings time.
    
        lon - longitude in decimal degrees (-180 to 180)
        lat - latitude in decimal degrees (-90 to 90)
    
    lon,lat will be converted to WellKnownText (WKT) and compared
    to polygons (using osgeo's Geometry.Contains method) from data
    sources or longitudinal boundaries
    
    
    Data Sources:
    US - timezones are read from USTimeZones.kml, which was obtained 
         from the web and reviewed for accuracy.

    Other - longitudinal position based on 15 degree intervals
    
    Example:
        >>> from geotz import get_tz
        >>> tzname, tzdict = get_tz(-74.0064, 40.7142)
        >>> print tzname
        America/New_York
        >>> print tzdict
        {'jan': -5.0, 'jul': -4.0, 'gmt': -5.0}
    """
    
    lon = lon % 360.;
    lon = (lon - 360) if lon > 180 else lon
    if lon > 180 or lon < -180:
        raise NotImplemented('Longitudes must be between -180 and 180')
    wkt = "POINT(%f %f)" % (lon,lat)
    # Old osgeo.ogr approach
    #oldpoint = ogr.CreateGeometryFromWkt(wkt)
    # Old osgeo.ogr approach
    # for feat in oldfeats:
    #    if feat.geometry().Contains(oldpoint):
    #        tz_key = feat.GetField(0)
    #        print tz_key

    point = loads(wkt)
    
    # For each timezone polygon, check if the point is
    # within the polygon and return if it is.
    # If it is not (else), then use longitude boundaries
    for tz_key, feat in usfeats:
        if feat.contains(point):
            return tz_key, dict([(k, float(v)) for k, v in tzdict[tz_key].iteritems()])
    else:
        for tz_key, feat in worldfeats:
            if feat.contains(point):
                return str(tz_key), dict([(k, float(tz_key)) for k in 'jul jan gmt'.split()])
        else:
            # Find timezone band with longitude
            for idx, (minl, maxl, off) in enumerate(lon_bounds):
                if lon > minl and lon <= maxl:
                    return 'lonbound(%.1f,%.1f)' % (minl, maxl), dict([(k, off) for k in 'jul jan gmt'.split()])

class TestOffsets(unittest.TestCase):
    def test_NewYorkUnitedStates(self):
        tsrc, tz = get_tz(lon = -74.0064, lat = 40.7142)
        # Checked using http://askgeo.com/
        self.assertEqual(tsrc, 'America/New_York')
        self.assertEqual(tz, dict(jul=-4., jan=-5., gmt=-5.))

    def test_NewYorkUnitedStates_PosLon(self):
        tsrc, tz = get_tz(lon = 360-74.0064, lat = 40.7142)
        # Checked using http://askgeo.com/
        self.assertEqual(tsrc, 'America/New_York')
        self.assertEqual(tz, dict(jul=-4., jan=-5., gmt=-5.))

    def test_NewYorkUnitedStates_NegLon(self):
        tsrc, tz = get_tz(lon = -360-74.0064, lat = 40.7142)
        self.assertEqual(tsrc, 'America/New_York')
        self.assertEqual(tz, dict(jul=-4., jan=-5., gmt=-5.))

    def test_LosAngelesUnitedStates(self):
        tsrc, tz = get_tz(lon = -118.2428, lat = 34.0522)
        # Checked using http://askgeo.com/
        self.assertEqual(tsrc, 'America/Los_Angeles')
        self.assertEqual(tz, {'jan': -8.0, 'jul': -7.0, 'gmt': -8.0})

    def test_offUSCoast(self):
        tsrc, tz = get_tz(lon = -130., lat = 26.27)
        self.assertEqual(tsrc, '-9')
        # Checked using http://askgeo.com/
        self.assertEqual(tz, dict(jul=-9., jan=-9., gmt=-9.))

    def test_MinskBelarus(self):
        tsrc, tz = get_tz(lon = 27.59765625, lat = 53.826596742994)
        # Checked using http://askgeo.com/
        self.assertEqual(tsrc, '2')
        self.assertEqual(tz, dict(jul=2., jan=2., gmt=2.))

    def test_LusakaZimbabwe(self):
        tsrc, tz = get_tz(lon = 28.323, lat = -15.485)
        # Checked using http://askgeo.com/
        self.assertEqual(tsrc, '2')
        self.assertEqual(tz, dict(jul=2., jan=2., gmt=2.))

if __name__ == '__main__':
    unittest.main()