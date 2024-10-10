"""
File name: "gridex.py"
This script provides functionality for indexing and querying GeoTIFF (.tif) files in a directory by extracting
their bounding box (MBR) and spatial reference information, and saving it in an index file (_index.csv).
It also enables querying of the index file to find GeoTIFF files that overlap with a given geometry.

Functions:

- create_index(directory):
    Scans a specified directory for .tif files, extracts their bounding boxes and spatial reference (SRID),
    and writes this information to an index file (_index.csv) in the same directory.

- get_epsg_code(dataset):
    Extracts the EPSG code (SRID) from a GeoTIFF dataset's projection information. Returns 'Unknown' if
    the SRID cannot be determined.

- query_index(directory, query_geometry):
    Reads the index file in a directory and returns a list of .tif files whose bounding boxes intersect
    with a provided query geometry in GeoJSON format.

- mbr_overlap(polygon_mbr, file_mbr):
    Checks if two bounding boxes (MBRs) overlap by comparing their minimum and maximum X/Y coordinates.

- index_directories_recursively(root_directory):
    Recursively searches through all subdirectories under the root directory for .tif files, and creates
    an index file in each directory that contains at least one .tif file. Skips directories that already
    have an _index.csv file.

- main():
    The entry point of the script. Takes a directory path as a command-line argument and recursively
    indexes all directories under the given path that contain .tif files.
"""


import os
import sys
import csv
from osgeo import gdal, osr, ogr

INDEX_FILE = "_index.csv"

# Enable GDAL exceptions for better error handling
gdal.UseExceptions()

def create_index(directory):
    """
    Scans a directory for .tif files, extracts their bounding box information (MBR),
    and creates an index file (_index.csv) in the directory.

    The index will have columns: ID, FileName, FileSize, x1, y1, x2, y2, SRID, Geometry4326.

    :param directory: The directory containing the .tif files to index.
    """
    index_path = os.path.join(directory, INDEX_FILE)

    # Open the index file for writing
    with open(index_path, mode='w', newline='') as index_file:
        writer = csv.writer(index_file, delimiter=';')

        # Write header: ID, FileName, FileSize, x1, y1, x2, y2, SRID, Geometry4326
        writer.writerow(["ID", "FileName", "FileSize", "x1", "y1", "x2", "y2", "SRID", "Geometry4326"])

        file_id = 0

        # Iterate through all .tif files in the directory
        for filename in os.listdir(directory):
            if filename.endswith(".tif"):
                file_path = os.path.join(directory, filename)

                # Open the TIFF file and extract its bounding box (MBR)
                dataset = gdal.Open(file_path)
                if dataset:
                    geo_transform = dataset.GetGeoTransform()
                    width = dataset.RasterXSize
                    height = dataset.RasterYSize

                    # Calculate the bounding box
                    min_x = geo_transform[0]
                    max_x = min_x + width * geo_transform[1]
                    min_y = geo_transform[3] + height * geo_transform[5]
                    max_y = geo_transform[3]

                    # Get the file size
                    file_size = os.path.getsize(file_path)

                    # Extract the SRID (EPSG code) from the dataset's projection
                    srid = get_epsg_code(dataset)

                    # Create the WKT geometry (polygon) based on the bounding box
                    wkt_polygon = f"POLYGON (({min_x} {min_y}, {max_x} {min_y}, {max_x} {max_y}, {min_x} {max_y}, {min_x} {min_y}))"

                    # Write the file information and its bounding box to the index file
                    writer.writerow([file_id, filename, file_size, min_x, min_y, max_x, max_y, srid, wkt_polygon])

                    # Increment the file ID
                    file_id += 1

                    # Close the dataset
                    dataset = None

    print(f"Index created at {index_path}")

def get_epsg_code(dataset):
    """
    Extract the EPSG code (SRID) from the GeoTIFF dataset's projection.

    :param dataset: The GDAL dataset of the GeoTIFF file.
    :return: The EPSG code (SRID) or 'Unknown' if it cannot be determined.
    """
    projection = dataset.GetProjection()
    if not projection:
        return "Unknown"

    # Use the SpatialReference object to extract the EPSG code
    spatial_ref = osr.SpatialReference(wkt=projection)
    if spatial_ref.IsProjected() or spatial_ref.IsGeographic():
        epsg_code = spatial_ref.GetAttrValue("AUTHORITY", 1)
        if epsg_code:
            return epsg_code

    return "Unknown"

def query_index(directory, query_geometry):
    """
    Reads the index file (_index.csv) in the directory and returns a list of .tif files
    whose bounding polygons overlap with the provided query geometry.

    :param directory: The directory containing the index file and .tif files.
    :param query_geometry: The query geometry (GeoJSON format).
    :return: A list of .tif file names that overlap with the query geometry.
    """
    index_path = os.path.join(directory, INDEX_FILE)
    overlapping_files = []

    # Convert the GeoJSON query geometry to an OGR geometry object
    query_geom = ogr.CreateGeometryFromJson(query_geometry)

    # Open the index file and read the geometries
    with open(index_path, mode='r') as index_file:
        reader = csv.DictReader(index_file, delimiter=';')

        for row in reader:
            # Get the WKT geometry for the file from the index
            file_geometry_wkt = row["Geometry4326"]

            # Convert the WKT geometry into an OGR geometry object
            file_geom = ogr.CreateGeometryFromWkt(file_geometry_wkt)

            # Check if the query geometry intersects with the file's geometry
            if query_geom.Intersects(file_geom):
                overlapping_files.append(row["FileName"])

    return overlapping_files

def mbr_overlap(polygon_mbr, file_mbr):
    """
    Checks if two bounding boxes (MBRs) overlap.

    :param polygon_mbr: The bounding box of the query geometry (minX, maxX, minY, maxY).
    :param file_mbr: The bounding box of a .tif file (minX, maxX, minY, maxY).
    :return: True if the bounding boxes overlap, False otherwise.
    """
    p_min_x, p_max_x, p_min_y, p_max_y = polygon_mbr
    f_min_x, f_max_x, f_min_y, f_max_y = file_mbr

    # Check for overlap
    return not (p_max_x < f_min_x or p_min_x > f_max_x or p_max_y < f_min_y or p_min_y > f_max_y)

def index_directories_recursively(root_directory):
    """
    Recursively index all directories that contain at least one .tif file under the root_directory.
    If a directory already contains an _index.csv file, skip creating a new one.

    :param root_directory: The root directory to start searching for .tif files.
    """
    for dirpath, _, filenames in os.walk(root_directory):
        # Check if there are any .tif files in the directory
        tif_files = [f for f in filenames if f.endswith('.tif')]

        if tif_files:
            index_path = os.path.join(dirpath, INDEX_FILE)

            # If the index file already exists, skip this directory
            if os.path.exists(index_path):
                print(f"Index file already exists in {dirpath}. Skipping.")
            else:
                print(f"Creating index for {dirpath}...")
                create_index(dirpath)

def main():
    """
    Main function to create an index for a directory of GeoTIFF (.tif) files and all its subdirectories.
    Takes the root directory path as a command-line argument.
    """
    if len(sys.argv) != 2:
        print("Usage: python gridex.py <directory>")
        sys.exit(1)

    root_directory = sys.argv[1]

    if not os.path.isdir(root_directory):
        print(f"Error: {root_directory} is not a valid directory")
        sys.exit(1)

    # Recursively index directories containing .tif files
    index_directories_recursively(root_directory)

if __name__ == "__main__":
    main()
