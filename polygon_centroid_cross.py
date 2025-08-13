#!/usr/bin/env python3
import sys
import os
import math
import random
import xml.etree.ElementTree as ET
import simplekml

def parse_first_polygon_coords(kml_path):
    tree = ET.parse(kml_path)
    root = tree.getroot()
    polygon = root.find(".//{*}Polygon")
    if polygon is None:
        return None, None, None

    placemark = root.find(".//{*}Placemark[{*}Polygon]")
    name_text = ""
    if placemark is not None:
        name_el = placemark.find("{*}name")
        if name_el is not None and name_el.text:
            name_text = name_el.text.strip()

    coords_el = polygon.find(".//{*}outerBoundaryIs//{*}LinearRing//{*}coordinates")
    if coords_el is None or not (coords_el.text and coords_el.text.strip()):
        coords_el = polygon.find(".//{*}coordinates")

    if coords_el is None or not (coords_el.text and coords_el.text.strip()):
        return name_text, None, root

    coords_text = coords_el.text.strip()
    coords = []
    for token in coords_text.replace("\n", " ").replace("\t", " ").split():
        parts = token.split(",")
        if len(parts) >= 2:
            try:
                lon = float(parts[0])
                lat = float(parts[1])
                coords.append((lon, lat))
            except ValueError:
                continue

    if len(coords) < 3:
        return name_text, None, root
    return name_text, coords, root

def polygon_centroid(coords):
    if coords[0] == coords[-1]:
        pts = coords[:-1]
    else:
        pts = coords
    A = 0.0
    Cx = 0.0
    Cy = 0.0
    n = len(pts)
    for i in range(n):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % n]
        cross = x1 * y2 - x2 * y1
        A += cross
        Cx += (x1 + x2) * cross
        Cy += (y1 + y2) * cross
    A *= 0.5
    if abs(A) < 1e-12:
        sx = sum(p[0] for p in pts)
        sy = sum(p[1] for p in pts)
        return sx / n, sy / n
    Cx /= (6.0 * A)
    Cy /= (6.0 * A)
    return Cx, Cy

def meters_to_deg_offsets(lat_deg, east_m, north_m):
    # Approx conversion on WGS84: 1 deg lat ~ 111_320 m; 1 deg lon ~ 111_320 * cos(lat)
    lat_rad = math.radians(lat_deg)
    dlat = north_m / 111320.0
    dlon = east_m / (111320.0 * max(math.cos(lat_rad), 1e-12))
    return dlon, dlat

def cross_path_coords(lon, lat, arm_m=10.0):
    # Points:
    # 1: centroid
    # 2: 10 m 0° (north) of centroid
    # 3: 10 m 180° (south) of centroid
    # 4: centroid
    # 5: 10 m 270° (west) of centroid
    # 6: 10 m 90° (east) of centroid
    # 7: centroid
    dlon_east, dlat_north = meters_to_deg_offsets(lat, arm_m, arm_m)
    # North/South (lat +/-)
    north = (lon, lat + dlat_north)
    south = (lon, lat - dlat_north)
    # East/West (lon +/-)
    east = (lon + dlon_east, lat)
    west = (lon - dlon_east, lat)
    seq = [
        (lon, lat),
        north,
        south,
        (lon, lat),
        west,
        east,
        (lon, lat),
    ]
    # KML uses lon,lat[,alt]
    return [(p[0], p[1]) for p in seq]

def rand_kml_abgr():
    # KML color is aabbggrr (alpha, blue, green, red) in hex.
    r = random.randint(0, 255)
    g = random.randint(0, 255)
    b = random.randint(0, 255)
    a = 255
    return f"{a:02x}{b:02x}{g:02x}{r:02x}"

def write_cross_linestring(kml_path, name, lat, lon, arm_m=10.0):
    kml_obj = simplekml.Kml()
    coords = cross_path_coords(lon, lat, arm_m=arm_m)
    ls = kml_obj.newlinestring(name=name or "Centroid cross", coords=coords)
    ls.altitudemode = simplekml.AltitudeMode.clamptoground
    ls.style.linestyle.width = 3
    ls.style.linestyle.color = rand_kml_abgr()
    title = os.path.splitext(os.path.basename(kml_path))[0]
    out_path = os.path.join(os.path.dirname(kml_path), f"{title}_centroid.kml")
    kml_obj.save(out_path)
    print(f"Centroid cross saved as {out_path}")

def main():
    if len(sys.argv) == 2:
        kml_path = sys.argv[1]
    else:
        kml_path = input("Enter kml location: ").strip()

    try:
        name, coords, _ = parse_first_polygon_coords(kml_path)
        if not coords:
            raise ValueError("The KML file does not contain a Polygon with coordinates.")
        lon, lat = polygon_centroid(coords)
        print(f"{lat},{lon}")  # stdout in lat,lon format
        write_cross_linestring(kml_path, name, lat, lon, arm_m=10.0)
    except Exception as e:
        print(f"Error processing file: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
