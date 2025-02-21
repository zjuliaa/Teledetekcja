import arcpy
from arcpy.sa import *
import os

workspace = r"C:\Users\user\Documents\ArcGIS\Projects\MyProject10\MyProject10.gdb"
arcpy.env.workspace = workspace
arcpy.env.overwriteOutput = True


raster_path = r"C:\sem5\Teledetekcja\sprawdzam\grupa_2.tif"

output_folder = os.path.dirname(raster_path)

if not arcpy.Exists(raster_path):
    raise FileNotFoundError(f"Plik {raster_path} nie istnieje lub nie jest wspierany.")

raster = Raster(raster_path)
band_count = raster.bandCount
print(f"Liczba bandów w rastrze: {band_count}")

for i in range(1, band_count + 1):  
    band_path = os.path.join(output_folder, f"Band_{i}.tif")
    arcpy.management.MakeRasterLayer(raster_path, "temp_layer", band_index=i)
    arcpy.management.CopyRaster("temp_layer", band_path)
    print(f"Band {i} zapisany jako {band_path}.")

arcpy.management.Delete("temp_layer")


green_band = os.path.join(output_folder, "Band_4.tif")  
nir_band = os.path.join(output_folder, "Band_8.tif")    
red_band = os.path.join(output_folder, "Band_5.tif")

green_raster = Raster(green_band)
nir_raster = Raster(nir_band)
red_raster = Raster(red_band)

ci_green_raster = (nir_raster / green_raster) - 1
ci_green_raster.save(workspace+"\\ci_green1")


ndwi_raster = (green_raster- nir_raster)/ (green_raster+nir_raster)
ndwi_raster.save(workspace+"\\NDWI")

ndvi_raster = (nir_raster- red_raster)/ (nir_raster+ red_raster)
ndvi_raster.save(workspace+"\\NDVI")

def statystyki(raster_path):
    mean = float(arcpy.GetRasterProperties_management(raster_path, "MEAN").getOutput(0).replace(",", "."))
    std = float(arcpy.GetRasterProperties_management(raster_path, "STD").getOutput(0).replace(",", "."))
    min_value = float(arcpy.GetRasterProperties_management(raster_path, "MINIMUM").getOutput(0).replace(",", "."))
    max_value = float(arcpy.GetRasterProperties_management(raster_path, "MAXIMUM").getOutput(0).replace(",", "."))
    return mean, std, min_value, max_value

mean_ndvi, std_ndvi, min_val_ndvi, max_val_ndvi = statystyki(ndvi_raster)
mean_ci, std_ci, min_val_ci, max_val_ci = statystyki(ci_green_raster)
mean_ndwi, std_ndwi, min_val_ndwi, max_val_ndwi = statystyki(ndwi_raster)

upper_bound_ci = max_val_ci
lower_bound_ci = mean_ci +1.5*std_ci
print("Przedział CI GREEN", upper_bound_ci, lower_bound_ci)

upper_bound_ndwi = min_val_ndwi + 0.13
lower_bound_ndwi = min_val_ndwi
print("Przedział NDWI", upper_bound_ndwi, lower_bound_ndwi)

upper_bound_ndvi = max_val_ndvi
lower_bound_ndvi = mean_ndvi+1.2*std_ndvi
print("Przedział NDVI", upper_bound_ndvi, lower_bound_ndvi)

ndwi_mask = Con((Raster(ndwi_raster) >= lower_bound_ndwi) & (Raster(ndwi_raster) <= upper_bound_ndwi), 1)
ndvi_mask = Con((Raster(ndvi_raster) >= lower_bound_ndvi) & (Raster(ndvi_raster) <= upper_bound_ndvi), 1)
ci_green_mask = Con((Raster(ci_green_raster) >= lower_bound_ci) & (Raster(ci_green_raster) <= upper_bound_ci), 1)

combined_mask = Con(~IsNull(ndvi_mask) | ~IsNull(ci_green_mask) | ~IsNull(ndwi_mask), 1)
mask_polygons = workspace+"\\mask_polygons"
arcpy.RasterToPolygon_conversion(combined_mask, mask_polygons, "SIMPLIFY", "Value")

arcpy.analysis.Near(
    in_features="mask_polygons",
    near_features="mask_polygons",
    search_radius="10 Meters",
    location="NO_LOCATION",
    angle="NO_ANGLE",
    method="PLANAR",
    field_names="NEAR_FID NEAR_FID;NEAR_DIST NEAR_DIST",
    distance_unit=""
)
 
arcpy.management.SelectLayerByAttribute(
    in_layer_or_view="mask_polygons",
    selection_type="NEW_SELECTION",
    where_clause="NEAR_DIST < 2",
    invert_where_clause=None
)
 
arcpy.conversion.ExportFeatures(
    in_features="mask_polygons",
    out_features=workspace+"\\wybrane"
)
 
arcpy.management.SelectLayerByAttribute("mask_polygons", "CLEAR_SELECTION")
 
arcpy.analysis.SpatialJoin(
    target_features="wybrane",
    join_features="mask_polygons",
    out_feature_class=arcpy.env.workspace + "\\wybrane_SpatialJoin",
    join_operation="JOIN_ONE_TO_ONE",
    join_type="KEEP_ALL",
    match_option="CLOSEST",
    search_radius="3 Meters"
)
 
arcpy.conversion.ExportFeatures(
    in_features="wybrane_SpatialJoin",
    out_features=arcpy.env.workspace + "\\lasy_ostateczne",
    where_clause="Shape_Area >= 1000"
)
