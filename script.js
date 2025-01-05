
const toggleButton = document.getElementById('toggle-controls');
const filters = document.getElementById('filters');

toggleButton.addEventListener('click', () => {
    const isHidden = filters.classList.contains('hidden');
    filters.classList.toggle('hidden');
});



// Initialisation de la carte
var map = L.map('map').setView([48.85908, 2.34688], 15);
// add Leaflet-Geoman controls with some options to the map  
map.pm.addControls({  
    position: 'topright',  
    drawCircleMarker: false,
    rotateMode: false,
  }); 
// Listen for the creation of shapes
map.on('pm:create', function (e) {
    const layer = e.layer; // The newly created layer (polygon or rectangle)

    if (layer instanceof L.Polygon || layer instanceof L.Rectangle) {
        // Calculate the area in square meters
        const latLngs = layer.getLatLngs()[0]; // Get the vertices of the shape
        const area = L.GeometryUtil.geodesicArea(latLngs); // Geodesic area in m²
        const areaInHectares = (area / 10000).toFixed(2); // Convert to hectares

        // Bind a popup to the layer with the area information
        layer.bindPopup(`Surface: ${areaInHectares} ha`).openPopup();
    }
});
// Ajout d'une couche de base OpenStreetMap
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map);


var vectorLayer;

// Fonction pour appliquer les filtres
function applyFilters() {
    if (vectorLayer) {
    map.removeLayer(vectorLayer);
    }

    var usageType = document.getElementById("usage-filter").value;
    var minHeight = parseFloat(document.getElementById("min-height").value) || 0;
    var maxHeight = parseFloat(document.getElementById("max-height").value) || Infinity;
    var minSurface = parseFloat(document.getElementById("surface-filter").value) || 0;
    var isolationType = document.getElementById("isolation-filter").value;
    var materialType = document.getElementById("material-filter").value;
    var floorType = document.getElementById("floor-filter").value;
    var minYear = parseInt(document.getElementById("min-year").value) || null; // Année minimale
    var maxYear = parseInt(document.getElementById("max-year").value) || null; // Année maximale
    var filteredColor = document.getElementById("filtered-color").value;
    var unfilteredColor = document.getElementById("unfiltered-color").value;


    
    fetch(`https://ilyasra1.pythonanywhere.com/get_filtered_data?categories=${encodeURIComponent(usageType)}&min_height=${minHeight}&max_height=${maxHeight}&min_surface=${minSurface}&isolation=${encodeURIComponent(isolationType)}&material=${encodeURIComponent(materialType)}&floor=${encodeURIComponent(floorType)}&min_year=${minYear}&max_year=${maxYear}`)
    .then(response => {
        if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        console.log('Données reçues depuis l’API :', data);
        document.getElementById("num-elements").textContent = `Nombre d'éléments filtrés : ${data.num_elements}`;
    })
    .catch(error => {
        console.error('Erreur lors de la récupération des données :', error);
        document.getElementById("num-elements").textContent = "Erreur : impossible de récupérer les données.";
    });

    // Charger et afficher les tuiles vectorielles filtrées
    vectorLayer = L.vectorGrid.protobuf(
    'https://api.maptiler.com/tiles/7ac1b707-2d6a-4766-aaee-be71f6b60979/{z}/{x}/{y}.pbf?key=bL66FVK5J4yUTp9TkgHD',
    {
        interactive: true,
        vectorTileLayerStyles: {
        me__bdnb__batiment_groupe_compile: function (properties) {
            // Vérifiez si tous les filtres sont vides
            var isFilterEmpty = !usageType && minHeight === 0 && maxHeight === Infinity && minSurface === 0 && !isolationType && !materialType && !floorType && minYear === null && maxYear === null;

            // Si aucun filtre n'est appliqué, afficher tous les bâtiments
            if (isFilterEmpty) {
            return { color: unfilteredColor, fill: true, fillColor: unfilteredColor, fillOpacity: 0.8, opacity: 0 };
            }
            var usageMatch = !usageType || (properties.bdtopo_bat_l_usage_1 && properties.bdtopo_bat_l_usage_1.toLowerCase().includes(usageType.toLowerCase()));
            var heightMatch = !isNaN(minHeight) && !isNaN(maxHeight) && properties.bdtopo_bat_hauteur_mean >= minHeight && properties.bdtopo_bat_hauteur_mean <= maxHeight;
            var surfaceMatch = properties.dpe_mix_arrete_surface_habitable_logement >= minSurface;
            var isolationMatch = isolationType === "" || (properties.dpe_mix_arrete_type_isolation_mur_exterieur && properties.dpe_mix_arrete_type_isolation_mur_exterieur.toLowerCase() === isolationType.toLowerCase());
            var materialMatch = materialType === "" || (properties.dpe_mix_arrete_materiaux_structure_mur_exterieur && properties.dpe_mix_arrete_materiaux_structure_mur_exterieur.toLowerCase() === materialType.toLowerCase());
            var floorMatch = !floorType || (properties.dpe_mix_arrete_type_plancher_bas_deperditif && properties.dpe_mix_arrete_type_plancher_bas_deperditif.toLowerCase().includes(floorType.toLowerCase()));
            
            // Extraction des années de construction
            var yearStrings = properties.rnc_l_annee_construction; // Supposons que c'est une chaîne comme '(1:1787)'
            var years = [];

            

            // Utiliser une expression régulière pour extraire les années
            var regex = /\d+:\d+/g; // Capture les paires de type "X:YYYY"
            var matches = yearStrings.match(regex);

            if (matches) {
            // Pour chaque match, extraire l'année
            matches.forEach(match => {
                var year = parseInt(match.split(':')[1]); // Prendre la partie après ':'
                if (!isNaN(year)) {
                years.push(year); // Ajouter l'année à la liste
                }
            });
            }

            // Vérifiez si les années extraites se situent dans la plage spécifiée
            var yearMatch = (minYear === null || years.some(year => year >= minYear)) && (maxYear === null || years.some(year => year <= maxYear));

            return (usageMatch && heightMatch && surfaceMatch && isolationMatch && materialMatch && floorMatch && yearMatch)
                ? { color: filteredColor, fill: true, fillColor: filteredColor, fillOpacity: 0.9, opacity: 0, interactive: true }
                : { color: unfilteredColor, fill: true, fillColor: unfilteredColor, fillOpacity: 0.7, opacity: 0, interactive: true };

        }
        }
    }
    );

    vectorLayer.on('click', function (event) {
    // Récupération des propriétés de la tuile cliquée
    var properties = event.layer.properties;

    // Création du contenu du popup
    var popupContent = `
        <b>Type d'usage :</b> ${properties.bdtopo_bat_l_usage_1 || 'N/A'}<br>
        <b>Hauteur moyenne :</b> ${properties.bdtopo_bat_hauteur_mean || 'N/A'} m<br>
        <b>Surface habitable :</b> ${properties.dpe_mix_arrete_surface_habitable_logement || 'N/A'} m²<br>
        <b>Type d'isolation :</b> ${properties.dpe_mix_arrete_type_isolation_mur_exterieur || 'Non spécifié'}<br>
        <b>Matériau des murs :</b> ${properties.dpe_mix_arrete_materiaux_structure_mur_exterieur || 'Non spécifié'}<br>
        <b>Type de plancher :</b> ${properties.dpe_mix_arrete_type_plancher_bas_deperditif || 'N/A'}<br>
        <b>Année de construction :</b> ${properties.rnc_l_annee_construction || 'N/A'}<br>
    `;

    // Affichage du popup
    L.popup()
    .setLatLng(event.latlng)
    .setContent(popupContent)
    .openOn(map);
    });

    vectorLayer.addTo(map);
}

// Ajout d'écouteurs pour le bouton d'application des filtres
document.getElementById("apply-filters").addEventListener("click", applyFilters);

// Charger les données initiales sans filtres
applyFilters();
