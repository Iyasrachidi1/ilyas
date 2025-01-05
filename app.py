import geopandas as gpd
from flask import Flask, jsonify, request
from flask_cors import CORS
import pandas as pd
import re

app = Flask(__name__)
CORS(app)

# Chemin vers le fichier GeoPackage
gpkg_file = "donnes.gpkg"

# Charger le fichier GeoPackage
gdf = gpd.read_file(gpkg_file)

@app.route('/get_filtered_data', methods=['GET'])
def get_filtered_data():
    # Récupérer les paramètres de la requête
    categories_to_filter = request.args.get('categories', '').split(',')
    min_height = float(request.args.get('min_height', 0))
    max_height = float(request.args.get('max_height', float('inf')))
    min_surface = float(request.args.get('min_surface', 0))
    isolation_type = request.args.get('isolation', '').strip().lower()
    material_type = request.args.get('material', '').strip().lower()
    floor_type = request.args.get('floor', '').strip().lower()
    min_year = request.args.get('min_year', None)
    max_year = request.args.get('max_year', None)

    # Convertir min_year et max_year en None ou int
    min_year = None if min_year in (None, 'null') else int(min_year)
    max_year = None if max_year in (None, 'null') else int(max_year)

    # Fonction de filtrage
    def filter_function(row):
    # Vérification de l'usage
        usage_match = all(
            cat.strip().lower() in str(row.get('bdtopo_bat_l_usage_1', '')).lower()
            for cat in categories_to_filter if cat.strip()
        ) if row.get('bdtopo_bat_l_usage_1') else False

        # Vérification de la hauteur
        height_match = (
            (min_height == 0 and max_height == float('inf')) or  # Aucun filtre appliqué
            (not pd.isnull(row.get('bdtopo_bat_hauteur_mean')) and 
            (min_height <= row['bdtopo_bat_hauteur_mean'] <= max_height))
        )

        # Vérification de la surface
        surface_match = (
            pd.isnull(row.get('dpe_mix_arrete_surface_habitable_logement')) or 
            (row['dpe_mix_arrete_surface_habitable_logement'] >= min_surface)
        )

        isolation_match = (
            not isolation_type or 
            (row.get('dpe_mix_arrete_type_isolation_mur_exterieur') is not None and 
            row['dpe_mix_arrete_type_isolation_mur_exterieur'].lower() == isolation_type.lower())
        )


        # Vérification du matériau
        material_match = (
            not material_type or
            (row.get('dpe_mix_arrete_materiaux_structure_mur_exterieur') is not None and 
            row['dpe_mix_arrete_materiaux_structure_mur_exterieur'].lower() == material_type.lower())
        )


        # Vérification du type de plancher
        floor_match = (
            not floor_type or
            (
                row.get('dpe_mix_arrete_type_plancher_bas_deperditif') is not None and
                floor_type.lower() in row['dpe_mix_arrete_type_plancher_bas_deperditif'].lower()
            )
        )


        # Vérification des années de construction
        year_strings = str(row.get('rnc_l_annee_construction', ''))  # Convertir en chaîne si nécessaire
        matches = re.findall(r'\d+:\d+', year_strings)  # Paires de type 'X:YYYY'
        years = [int(match.split(':')[1]) for match in matches if match.split(':')[1].isdigit()]
        
        year_match = (
            (min_year is None or any(year >= min_year for year in years)) and
            (max_year is None or any(year <= max_year for year in years))
        )

        # Combinaison de toutes les conditions
        return (
            usage_match and height_match and surface_match and
            isolation_match and material_match and floor_match and year_match
        )
    # Appliquer les filtres
    filtered_gdf = gdf[gdf.apply(filter_function, axis=1)]

    # Comptage
    num_elements = filtered_gdf.shape[0]

    # Convertir en GeoJSON
    filtered_geojson = filtered_gdf.to_crs(epsg=4326).to_json()

    # Retourner les résultats
    return jsonify({
        'num_elements': num_elements,
        'data': filtered_geojson
    })

if __name__ == '__main__':
    app.run(debug=True)
