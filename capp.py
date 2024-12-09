import geopandas as gpd
import folium
import streamlit as st
from streamlit_folium import folium_static
import requests
from io import BytesIO

# URL to the GPKG file on GitHub
gpkg_url = "https://github.com/Iyasrachidi1/ilyas/raw/master/donnes.gpkg"

# Télécharger le fichier GPKG depuis GitHub
response = requests.get(gpkg_url)

# Vérifier si la requête a réussi
if response.status_code == 200:
    # Lire le fichier GPKG téléchargé dans un GeoDataFrame
    gdf = gpd.read_file(BytesIO(response.content))

    # Filtrer uniquement les géométries de type Polygon ou MultiPolygon
    gdf = gdf[gdf['geometry'].apply(lambda x: x.geom_type in ['Polygon', 'MultiPolygon'])]

    # Supprimer les géométries invalides ou manquantes
    gdf = gdf[gdf['geometry'].notna()]
    gdf = gdf[gdf['geometry'].apply(lambda geom: not geom.is_empty and geom.is_valid)]

    # Conversion du système de coordonnées à EPSG:4326 (WGS84)
    if gdf.crs != 'EPSG:4326':
        st.sidebar.write("Conversion des géométries vers EPSG:4326 (WGS84)...")
        gdf = gdf.to_crs(epsg=4326)

    # Vérification des données géométriques
    st.sidebar.write(f"Nombre de polygones valides : {len(gdf)}")

    # Création de la carte Folium centrée sur les polygones
    centroids = gdf.geometry.centroid
    center = [centroids.y.mean(), centroids.x.mean()]
    m = folium.Map(location=center, zoom_start=12)

    # Affichage des polygones et multipolygones sur la carte avec popups
    for _, row in gdf.iterrows():
        if row['geometry'].is_valid:
            # Construction du contenu du popup avec les colonnes spécifiques
            popup_content = f"<b>ID bâtiment :</b> {row.get('batiment_groupe_id', 'N/A')}<br>"
            popup_content += f"<b>Code IRIS :</b> {row.get('code_iris', 'N/A')}<br>"
            popup_content += f"<b>Hauteur moyenne :</b> {row.get('bdtopo_bat_hauteur_mean', 'N/A')} m<br>"
            popup_content += f"<b>Usage principal :</b> {row.get('bdtopo_bat_l_usage_1', 'N/A')}<br>"
            popup_content += f"<b>Année de construction :</b> {row.get('rnc_l_annee_construction', 'N/A')}<br>"
            popup_content += f"<b>Surface habitable :</b> {row.get('dpe_mix_arrete_surface_habitable_logement', 'N/A')} m²<br>"
            popup_content += f"<b>Type isolation mur extérieur :</b> {row.get('dpe_mix_arrete_type_isolation_mur_exterieur', 'N/A')}<br>"
            popup_content += f"<b>Matériaux murs extérieurs :</b> {row.get('dpe_mix_arrete_materiaux_structure_mur_exterieur', 'N/A')}<br>"

            # Si la géométrie est un Polygon
            if row['geometry'].geom_type == 'Polygon':
                folium.Polygon(
                    locations=[(lat, lon) for lon, lat in row['geometry'].exterior.coords],
                    color='blue',
                    fill=True,
                    fill_color='blue',
                    fill_opacity=0.4,
                    popup=folium.Popup(popup_content, max_width=300)
                ).add_to(m)

            # Si la géométrie est un MultiPolygon
            elif row['geometry'].geom_type == 'MultiPolygon':
                for poly in row['geometry'].geoms:
                    folium.Polygon(
                        locations=[(lat, lon) for lon, lat in poly.exterior.coords],
                        color='blue',
                        fill=True,
                        fill_color='blue',
                        fill_opacity=0.4,
                        popup=folium.Popup(popup_content, max_width=300)
                    ).add_to(m)

    # Afficher la carte dans Streamlit
    folium_static(m)

else:
    st.error("Erreur lors du téléchargement du fichier GPKG.")
