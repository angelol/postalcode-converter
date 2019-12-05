# Download data here:
# https://mygeodata.cloud/osm/data/download/
import csv, sys, re, json
from collections import defaultdict
from shapely.geometry import Polygon
from shapely.ops import cascaded_union

### Settings ###
should_combine = True
should_separate_overlapping = True
epsilon = 0.000005
zip_code_property_name = 'name' # For London
# zip_code_property_name = 'postal_code' # For Vienna

files = sys.argv[1:]
class PolygonData:
    zip_code = None
    polygon = None 
    
    def __str__(self):
        return format_for_google(self.polygon)
        
    def __init__(self, zip_code, polygon):
        self.zip_code = zip_code
        self.polygon = polygon
        
    def __lt__(self, other):
        return self.zip_code.__lt__(other.zip_code)
        
    def __getitem__(self, index):
        if index == 0:
            return self.zip_code
        elif index == 1:
            return self.polygon
        else:
            raise IndexError

def main():
    for file in files:
        print("Processing ", file)
        main2(file)

def main2(file):
    j = json.loads(open(file).read())
    features = j['features']
    areas = [x for x in features if x['properties'][zip_code_property_name]]
    polygons = [PolygonData(x['properties'][zip_code_property_name], get_polygon(x)) for x in areas]
    
    if should_combine:
        polygons = cumulate(polygons)
    
    polygons.sort()
    
    # Algorithm to separate overlapping polygons into distinct ones
    if should_separate_overlapping:
        for x in polygons:
            buffer = x.polygon.boundary.buffer(epsilon)
            x.polygon = x.polygon.difference(buffer).simplify(epsilon*2)
        
    # Check to see which are still overlapping. There might be a legitimate reason for it. It's not always an error.
    for x in polygons:
        for y in polygons:
            if x.zip_code != y.zip_code:
                if x.polygon.intersects(y.polygon):
                    print("WARN: %s intersects with %s" % (x.zip_code, y.zip_code))
                    # assert not x.polygon.intersects(y.polygon)
                    
    # Now write to CSV file
    if should_combine:
        outname = "converted/%s-converted-combined.csv" % file
    else:
        outname = "converted/%s-converted.csv" % file
    writer = csv.writer(open(outname, 'w', encoding='utf-8'), quoting=csv.QUOTE_ALL)
    for zip_code, polygon in polygons:
        writer.writerow([zip_code, format_for_google(polygon)])

regex = re.compile(r'([A-Z]{1,2})([0-9]{1,2})([A-Z]*)')
"""
 Combines areas EC1A and EC1B and so forth to a larger area EC1
"""
def cumulate(polygons):
    new_list = defaultdict(list)
    unique_zip_codes = list(set([x.zip_code for x in polygons]))
    buckets = set()
    for zip_code in unique_zip_codes:
        main, number, subdesignation = regex.findall(zip_code)[0]
        buckets.add(main+number)
    
    for p in polygons:
        main, number, subdesignation = regex.findall(p.zip_code)[0]
        if (main + number) in buckets:
            new_list[main+number].append(p)
    
    out = []
    for name, p in new_list.items():
        combined_polygon = cascaded_union([x.polygon for x in p])
        out.append(PolygonData(name, combined_polygon))
    return out
        
        
    
def format_for_google(polygon):
    coords = []
    for a, b in polygon.exterior.coords:
        coords.append("%s:%s" % (b, a))
    return "|".join(coords)
    


def get_polygon(area):
    return Polygon(area['geometry']['coordinates'][0])
    
    
main()