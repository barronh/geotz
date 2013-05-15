__all__ = ['get_tz']

import pickle
import os
import sys
import csv
from warnings import warn

from shapely.wkt import loads
from shapely.prepared import prep


# timeZones.txt came from http://download.geonames.org/
tzdata = csv.reader(file(os.path.join(os.path.dirname(__file__), 'timeZones.txt')), delimiter = '\t')
tzdata.next()
tzdict = dict([(n, dict(lst = float(g), ldt = float(d), gmt = float(r))) for n,g,d,r in tzdata])

# Define data for longitude-based timezones
# no daylight savings time, so just one offset value
lon_offsets = [-11., -10.,  -9.,  -8.,  -7.,  -6.,  -5.,  -4.,  -3.,  -2.,  -1.,
                 0.,   1.,   2.,   3.,   4.,   5.,   6.,   7.,   8.,   9.,  10.,
                11.,  12., -12.]
lon_bounds = [[-172.5, -157.5],
              [-157.5, -142.5],
              [-142.5, -127.5],
              [-127.5, -112.5],
              [-112.5,  -97.5],
              [ -97.5,  -82.5],
              [ -82.5,  -67.5],
              [ -67.5,  -52.5],
              [ -52.5,  -37.5],
              [ -37.5,  -22.5],
              [ -22.5,   -7.5],
              [  -7.5,    7.5],
              [   7.5,   22.5],
              [  22.5,   37.5],
              [  37.5,   52.5],
              [  52.5,   67.5],
              [  67.5,   82.5],
              [  82.5,   97.5],
              [  97.5,  112.5],
              [ 112.5,  127.5],
              [ 127.5,  142.5],
              [ 142.5,  157.5],
              [ 157.5,  172.5],
              [ 172.5,  180. ],
              [ 180. ,  187.5]]

pklpath = os.path.join(os.path.dirname(__file__),'USTimeZones.pkl')

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
    outfeat = file(pklpath, 'w')
    featout = [(feat.GetField(0), feat.GetGeometryRef().ExportToWkt()) for feat in oldfeats]
    pickle.dump(featout, file(pklpath, 'w'))

if not os.path.exists(pklpath):
    print "Creating pkl file"
    makepkl()

# Load shape definitions as a list of tuples 
# that define timezones using Well Known Text (WKT)
# polygons
#
# [(tzname, Polygon definition), ...]
featsdict = pickle.load(file(pklpath))

# Convert WKT to shapely prepared shapes
# Preparing shapes improve repeated use, but
# slows import time
feats = [(k, prep(loads(v))) for k, v in featsdict if v is not None]



def get_tz(lon, lat):
    """
    Takes longitude and latitude and returns a string identifying
    the source of timezone information and a dictionary with 
    a time offset to get Local Daylight Time (ldt), Local Standard
    Time (lst), or Greenwich Mean Time (gmt).
    
        lon - longitude in decimal degrees (-180 to 180)
        lat - latitude in decimal degrees (-90 to 90)
    
    lon,lat will be converted to WellKnownText (WKT) and compared
    to polygons (using osgeo's Geometry.Contains method) from data
    sources or longitudinal boundaries
    
    
    Data Sources:
    US - timezones are read from USTimeZones.kml, which was obtained 
         from the web and reviewed for accuracy.

    Other - longitudinal position based on 15 degree intervals
    """
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
    for tz_key, feat in feats:
        if feat.contains(point):
            return tz_key, dict([(k, float(v)) for k, v in tzdict[tz_key].iteritems()])
    else:
        # Find timezone band with longitude
        for idx, (minl, maxl) in enumerate(lon_bounds):
            if lon > minl and lon <= maxl:
                return 'lonbound(%.1f,%.1f)' % (minl, maxl), dict([(k, lon_offsets[idx]) for k in 'ldt lst gmt'.split()])

if __name__ == '__main__':
    print 'Running tests (4)'
    try:
        tsrc, tz = get_tz(lon = -79.92, lat = 37.75)
        # Checked using http://askgeo.com/
        assert(tz == dict(ldt=-4., lst=-5., gmt=-5.))
        print 'PASSED: US timezone check (1/4)'
    except Exception as e:
        print 'FAILED: US timezone check (1/4)', str(e)
    try:
        tsrc, tz = get_tz(lon = 360-79.92, lat = 37.75)
        # Checked using http://askgeo.com/
        assert(tz == dict(ldt=-4., lst=-5., gmt=-5.))
        print 'FAILED: US timezone check (2/4) -- should have errored when lon is > 180'
    except:
        print 'PASSED: US timezone check (2/4)'
    try:
        tsrc, tz = get_tz(lon = -181.92, lat = 37.75)
        # Checked using http://askgeo.com/
        assert(tz == dict(ldt=-4., lst=-5., gmt=-5.))
        print 'FAILED: US timezone check (3/4) -- should have errored when lon is > 180'
    except:
        print 'PASSED: US timezone check (3/4)'

    try:
        tsrc, tz = get_tz(lon = -130., lat = 26.27)
        # Checked using http://askgeo.com/
        assert(tz == dict(ldt=-9., lst=-9., gmt=-9.))
        print 'PASSED: longitude timezone check (4/4)'
    except Exception as e:
        print 'FAILED: US timezone check (4/4)', str(e)
