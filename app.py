import geopandas as gpd
from flask import Flask, jsonify, request
from flask_cors import CORS
import pandas as pd
import re
import os
import requests

app = Flask(__name__)
CORS(app)


# URL brute du fichier sur GitHub
GPKG_URL = "https://raw.githubusercontent.com/Iyasrachidi1/ilyas/master/donnes.gpkg"
LOCAL_GPKG_FILE = "donnes.gpkg"

# Télécharger le fichier s'il n'existe pas localement
if not os.path.exists(LOCAL_GPKG_FILE):
    print("🔄 Téléchargement du fichier GeoPackage...")
    response = requests.get(GPKG_URL)
    if response.status_code == 200:
        with open(LOCAL_GPKG_FILE, 'wb') as f:
            f.write(response.content)
        print("✅ Fichier GeoPackage téléchargé avec succès.")
    else:
        raise Exception(f"❌ Erreur lors du téléchargement du fichier: {response.status_code}")

# Charger le fichier GeoPackage
try:
    gdf = gpd.read_file(LOCAL_GPKG_FILE)
    print("✅ Fichier GeoPackage chargé avec succès.")
except Exception as e:
    raise Exception(f"❌ Erreur lors du chargement du fichier GeoPackage: {e}")



@app.route('/get_filtered_data', methods=['GET'])
def get_filtered_data():
    categories_to_filter = request.args.get('categories', '').split(',')
    min_height = float(request.args.get('min_height', 0))
    max_height = float(request.args.get('max_height', float('inf')))
    min_surface = float(request.args.get('min_surface', 0))
    isolation_type = request.args.get('isolation', '').strip().lower()
    material_type = request.args.get('material', '').strip().lower()
    floor_type = request.args.get('floor', '').strip().lower()
    min_year = request.args.get('min_year', None)
    max_year = request.args.get('max_year', None)

    min_year = None if min_year in (None, 'null') else int(min_year)
    max_year = None if max_year in (None, 'null') else int(max_year)

    def filter_function(row):
        usage_match = all(
            cat.strip().lower() in str(row.get('bdtopo_bat_l_usage_1', '')).lower()
            for cat in categories_to_filter if cat.strip()
        ) if row.get('bdtopo_bat_l_usage_1') else False

        height_match = (
            (min_height == 0 and max_height == float('inf')) or
            (not pd.isnull(row.get('bdtopo_bat_hauteur_mean')) and 
            (min_height <= row['bdtopo_bat_hauteur_mean'] <= max_height))
        )

        surface_match = (
            pd.isnull(row.get('dpe_mix_arrete_surface_habitable_logement')) or 
            (row['dpe_mix_arrete_surface_habitable_logement'] >= min_surface)
        )

        isolation_match = (
            not isolation_type or 
            (row.get('dpe_mix_arrete_type_isolation_mur_exterieur') is not None and 
            row['dpe_mix_arrete_type_isolation_mur_exterieur'].lower() == isolation_type.lower())
        )

        material_match = (
            not material_type or
            (row.get('dpe_mix_arrete_materiaux_structure_mur_exterieur') is not None and 
            row['dpe_mix_arrete_materiaux_structure_mur_exterieur'].lower() == material_type.lower())
        )

        floor_match = (
            not floor_type or
            (
                row.get('dpe_mix_arrete_type_plancher_bas_deperditif') is not None and
                floor_type.lower() in row['dpe_mix_arrete_type_plancher_bas_deperditif'].lower()
            )
        )

        year_strings = str(row.get('rnc_l_annee_construction', ''))
        matches = re.findall(r'\d+:\d+', year_strings)
        years = [int(match.split(':')[1]) for match in matches if match.split(':')[1].isdigit()]
        
        year_match = (
            (min_year is None or any(year >= min_year for year in years)) and
            (max_year is None or any(year <= max_year for year in years))
        )

        return (
            usage_match and height_match and surface_match and
            isolation_match and material_match and floor_match and year_match
        )

    filtered_gdf = gdf[gdf.apply(filter_function, axis=1)]
    num_elements = filtered_gdf.shape[0]
    filtered_geojson = filtered_gdf.to_crs(epsg=4326).to_json()

    return jsonify({
        'num_elements': num_elements,
        'data': filtered_geojson
    })

if __name__ == '__main__':
    app.run(debug=True)
