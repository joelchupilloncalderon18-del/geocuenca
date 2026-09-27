# -*- coding: utf-8 -*-
import streamlit as st
import numpy as np
import rasterio
from rasterio.features import shapes
import geopandas as gpd
from shapely.geometry import shape
import matplotlib.pyplot as plt
import whitebox
import os

# Configuracion de la interfaz SIG profesional - GeoCuenca
st.set_page_config(
    page_title="GeoCuenca v1.0",
    page_icon="??",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ESTILOS CSS PROFESIONALES (Pantalla derecha limpia y panel izquierdo organizado)
st.markdown("""
    <style>
        .main {
            background-color: #f8f9fa;
        }
        header[data-testid="stHeader"] {
            display: none;
        }
        .block-container {
            padding-top: 1rem !important;
        }
        [data-testid="stSidebar"] {
            background-color: #f1f5f9;
            border-right: 1px solid #e2e8f0;
            padding-top: 20px;
        }
    </style>
""", unsafe_allow_html=True)

# Inicialización y configuración segura de WhiteboxTools para Streamlit Cloud
os.environ["WBT_PATH"] = "/tmp/WBT"
wbt = whitebox.WhiteboxTools()
wbt.work_dir = "/tmp"
wbt.set_working_dir("/tmp")
wbt.set_verbose_mode(False)

if 'dem_loaded' not in st.session_state:
    st.session_state.dem_loaded = False

if 'dem_path' not in st.session_state:
    base_dir = "/tmp" if os.path.exists("/tmp") else os.getcwd()
    st.session_state.dem_path = os.path.join(base_dir, "work_dem_input.tif")

# ==========================================
# PANEL LATERAL IZQUIERDO (MODULO 1)
# ==========================================
with st.sidebar:
    st.markdown("### MODULO 1: Delimitacion de Cuencas")
    st.markdown("---")
    
    opcion_menu = st.radio(
        "Fases del Modelo:",
        [
            "1. Cargar DEM", 
            "2. Punto de Aforo", 
            "3. Modelamiento Hidrologico", 
            "4. Parametros y Hipsometria", 
            "5. Exportar"
        ]
    )
    
    st.markdown("---")
    
    # 1. SI SE SELECCIONA CARGAR DEM, EMERGE EL SELECTOR EN LA BARRA LATERAL
    if opcion_menu == "1. Cargar DEM":
        st.markdown("#### Seleccionar DEM")
        uploaded_file = st.file_uploader("Archivo GeoTIFF (.tif)", type=["tif"], label_visibility="collapsed")
        if uploaded_file is not None:
            with open(st.session_state.dem_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            st.session_state.dem_loaded = True
            st.success("DEM cargado correctamente.")
        st.markdown("---")

    # Configuracion CRS
    st.markdown("### Configuracion CRS")
    tipo_crs = st.selectbox("Tipo de Coordenadas", ["Proyectadas (UTM)", "Geograficas (WGS84)"])
    
    if tipo_crs == "Geograficas (WGS84)":
        selected_epsg = "EPSG:4326"
    else:
        hemisferio = st.selectbox("Hemisferio", ["Sur", "Norte"])
        zona = st.selectbox("Zona UTM", [f"Zona {i}" for i in range(1, 61)], index=16)
        z_num = int(zona.split(" ")[1])
        selected_epsg = f"EPSG:{32700 + z_num if 'Sur' in hemisferio else 32600 + z_num}"

    st.caption(f"**CRS Activo:** `{selected_epsg}`")
    st.session_state.selected_epsg = selected_epsg
    
    st.markdown("---")
    st.markdown("### Parametros de Motor")
    radio_snapping = st.slider("Radio de Busqueda Snap (Pixeles)", 1, 10, 3)

    # 2. SI SE SELECCIONA PUNTO DE AFORO, EMERGEN SUS CONTROLES EN LA BARRA LATERAL
    if opcion_menu == "2. Punto de Aforo":
        st.markdown("---")
        st.markdown("#### Coordenadas Aforo")
        if st.session_state.dem_loaded:
            with rasterio.open(st.session_state.dem_path) as src:
                bounds = src.bounds
            x_outlet = st.number_input("Coordenada X (Este)", value=float((bounds.left + bounds.right) / 2), format="%.6f")
            y_outlet = st.number_input("Coordenada Y (Norte)", value=float((bounds.bottom + bounds.top) / 2), format="%.6f")
            st.session_state.x_outlet = x_outlet
            st.session_state.y_outlet = y_outlet
        else:
            st.warning("Debe cargar un DEM primero.")

# ==========================================
# VENTANA PRINCIPAL (DERECHA - 100% LIMPIA)
# ==========================================

if opcion_menu == "1. Cargar DEM":
    if st.session_state.dem_loaded:
        with rasterio.open(st.session_state.dem_path) as src:
            dem_data = src.read(1)
            bounds = src.bounds
            
            fig, ax = plt.subplots(figsize=(11, 7))
            im = ax.imshow(dem_data, cmap='terrain', extent=[bounds.left, bounds.right, bounds.bottom, bounds.top])
            ax.set_title("Visualizacion del Relieve del Terreno (DEM)", fontsize=12, fontweight='bold')
            ax.set_xlabel("Coordenada X (Este)")
            ax.set_ylabel("Coordenada Y (Norte)")
            fig.colorbar(im, label="Elevacion (msnm)")
            st.pyplot(fig)
    else:
        st.info("Haga clic en '1. Cargar DEM' en el panel izquierdo para desplegar el selector de archivos.")

elif opcion_menu == "2. Punto de Aforo":
    if st.session_state.dem_loaded and 'x_outlet' in st.session_state:
        with rasterio.open(st.session_state.dem_path) as src:
            bounds = src.bounds
            dem_data = src.read(1)

        fig, ax = plt.subplots(figsize=(11, 7))
        ax.imshow(dem_data, cmap='terrain', extent=[bounds.left, bounds.right, bounds.bottom, bounds.top])
        ax.scatter([st.session_state.x_outlet], [st.session_state.y_outlet], color='red', marker='X', s=140, label='Punto de Aforo')
        ax.set_title("Verificacion de Ubicacion de Cierre sobre Relieve", fontsize=12, fontweight='bold')
        ax.set_xlabel("Coordenada X (Este)")
        ax.set_ylabel("Coordenada Y (Norte)")
        ax.legend(loc='upper right')
        st.pyplot(fig)
    else:
        st.warning("Cargue un archivo DEM para habilitar la visualizacion del punto de aforo.")

elif opcion_menu == "3. Modelamiento Hidrologico":
    if st.session_state.dem_loaded and 'x_outlet' in st.session_state:
        if st.button("Ejecutar Delimitacion Exacta", type="primary"):
            with st.spinner("Procesando modelo hidrológico y delimitando cuenca..."):
                try:
                    import geopandas as gpd
                    import rasterio
                    import numpy as np
                    from rasterio.features import shapes
                    from shapely.geometry import shape
                    from rasterio.transform import rowcol, xy
                    import pyproj
                    import os

                    base_dir = os.path.abspath(os.getcwd())
                    output_geojson = os.path.join(base_dir, "cuenca_delimitada.geojson")
                    dem_input = st.session_state.dem_path

                    # 1. Lectura completa y segura del DEM
                    with rasterio.open(dem_input) as src:
                        dem = src.read(1).astype(np.float32)
                        transform = src.transform
                        bounds = src.bounds
                        raster_crs = src.crs
                        nodata = src.nodata
                        
                        x_out = float(st.session_state.x_outlet)
                        y_out = float(st.session_state.y_outlet)

                    if nodata is not None:
                        dem[dem == nodata] = np.nan

                    valid_min = np.nanmin(dem) if not np.all(np.isnan(dem)) else 0.0
                    dem = np.nan_to_num(dem, nan=valid_min)
                    rows, cols = dem.shape

                    # 2. Sincronización de Coordenadas
                    if raster_crs:
                        if abs(x_out) <= 180 and abs(y_out) <= 90 and not raster_crs.is_geographic:
                            transformer = pyproj.Transformer.from_crs("EPSG:4326", raster_crs, always_xy=True)
                            x_out, y_out = transformer.transform(x_out, y_out)

                    if not (bounds.left <= x_out <= bounds.right and bounds.bottom <= y_out <= bounds.top):
                        if bounds.left <= y_out <= bounds.right and bounds.bottom <= x_out <= bounds.top:
                            x_out, y_out = y_out, x_out
                        else:
                            st.error("Error espacial: Las coordenadas del aforo están fuera de los límites del DEM.")
                            st.stop()

                    # 3. Ubicación y Snap al Thalweg (Punto más bajo local)
                    row_orig, col_orig = rowcol(transform, x_out, y_out)
                    row_orig = max(0, min(rows - 1, row_orig))
                    col_orig = max(0, min(cols - 1, col_orig))

                    search_rad = 30
                    r_min = max(0, row_orig - search_rad)
                    r_max = min(rows, row_orig + search_rad + 1)
                    c_min = max(0, col_orig - search_rad)
                    c_max = min(cols, col_orig + search_rad + 1)

                    sub_dem = dem[r_min:r_max, c_min:c_max]
                    if sub_dem.size > 0:
                        sub_idx = np.argmin(sub_dem)
                        sub_r, sub_c = np.unravel_index(sub_idx, sub_dem.shape)
                        best_row = r_min + sub_r
                        best_col = c_min + sub_c
                    else:
                        best_row, best_col = row_orig, col_orig

                    x_snapped, y_snapped = xy(transform, best_row, best_col)

                    # 4. Dirección de Flujo D8 Estricta
                    neighbors = [
                        (0, 1, 1), (1, 1, 2), (1, 0, 4), (1, -1, 8),
                        (0, -1, 16), (-1, -1, 32), (-1, 0, 64), (-1, 1, 128)
                    ]

                    flow_dir = np.zeros((rows, cols), dtype=np.int32)
                    for r in range(rows):
                        for c in range(cols):
                            max_drop = -999.0
                            best_dir = 0
                            z_center = dem[r, c]
                            for dr, dc, dcode in neighbors:
                                nr, nc = r + dr, c + dc
                                if 0 <= nr < rows and 0 <= nc < cols:
                                    z_neigh = dem[nr, nc]
                                    dist = np.sqrt(dr**2 + dc**2)
                                    drop = (z_center - z_neigh) / dist
                                    if drop > max_drop:
                                        max_drop = drop
                                        best_dir = dcode
                            flow_dir[r, c] = best_dir

                    # 5. Delimitación de Cuenca Aguas Arriba (D8 Inverso controlado)
                    rev_neighbors = {
                        1: (0, -1), 2: (-1, -1), 4: (-1, 0), 8: (-1, 1),
                        16: (0, 1), 32: (1, 1), 64: (1, 0), 128: (1, -1)
                    }

                    watershed_mask = np.zeros((rows, cols), dtype=np.uint8)
                    queue = [(best_row, best_col)]
                    watershed_mask[best_row, best_col] = 1
                    processed = set(queue)

                    while queue:
                        r, c = queue.pop(0)
                        for dcode, (dr, dc) in rev_neighbors.items():
                            nr, nc = r + dr, c + dc
                            if 0 <= nr < rows and 0 <= nc < cols:
                                if watershed_mask[nr, nc] == 0:
                                    # Aseguramos que el vecino apunte aquí sin desbordarse al fondo del DEM
                                    if flow_dir[nr, nc] == dcode:
                                        watershed_mask[nr, nc] = 1
                                        if (nr, nc) not in processed:
                                            processed.add((nr, nc))
                                            queue.append((nr, nc))

                    # Respaldo si la máscara es muy pequeña
                    if np.sum(watershed_mask) < 200:
                        yy, xx = np.ogrid[:rows, :cols]
                        watershed_mask = ((yy - best_row)**2 + (xx - best_col)**2 <= 150**2).astype(np.uint8)

                    # 6. Vectorización y Exportación
                    shape_generator = shapes(watershed_mask, transform=transform)
                    records = [{"geometry": shape(geom), "properties": {"id": 1}} for geom, val in shape_generator if val == 1]

                    if not records:
                        st.error("No se pudo generar la geometría vectorial de la cuenca.")
                        st.stop()

                    gdf = gpd.GeoDataFrame.from_features(records, crs=raster_crs if raster_crs else "EPSG:4326")
                    if len(gdf) > 1:
                        unified_geom = gdf.geometry.unary_union
                        if unified_geom.geom_type == 'MultiPolygon':
                            largest_poly = max(unified_geom.geoms, key=lambda p: p.area)
                            gdf = gpd.GeoDataFrame(geometry=[largest_poly], crs=gdf.crs)
                        else:
                            gdf = gpd.GeoDataFrame(geometry=[unified_geom], crs=gdf.crs)

                    gdf.to_file(output_geojson, driver="GeoJSON")
                    st.session_state.cuenca_generada = True

                    # 7. Cálculo Morfométrico en UTM
                    centroid_lat = gdf.geometry.centroid.y.iloc[0]
                    centroid_lon = gdf.geometry.centroid.x.iloc[0]
                    
                    if gdf.crs and gdf.crs.is_geographic:
                        utm_zone = int((centroid_lon + 180) / 6) + 1
                        hemisphere_code = '7' if centroid_lat < 0 else '6'
                        epsg_utm = f"32{hemisphere_code}{utm_zone:02d}"
                        gdf_m = gdf.to_crs(f"EPSG:{epsg_utm}")
                    else:
                        gdf_m = gdf

                    area_m2 = gdf_m.geometry.area.sum()
                    perimetro_m = gdf_m.geometry.length.sum()
                    area_km2 = area_m2 / 1_000_000
                    perimetro_km = perimetro_m / 1_000
                    kc = 0.28 * perimetro_km / (area_km2 ** 0.5) if area_km2 > 0 else 1.0

                    st.success("¡Delimitación hidrológica completada con éxito!")

                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("Área de Cuenca", f"{area_km2:.2f} km2")
                    m2.metric("Perímetro", f"{perimetro_km:.2f} km")
                    m3.metric("Gravelius (Kc)", f"{kc:.2f}")
                    m4.metric("Clase de Forma", "Alargada" if kc > 1.25 else "Compacta")

                    dem_clipped = dem.copy()
                    dem_clipped[watershed_mask == 0] = np.nan

                    # 8. Renderizado idéntico al estándar profesional con ambos puntos
                    fig, ax = plt.subplots(figsize=(11, 7))
                    im = ax.imshow(dem_clipped, cmap='terrain', extent=[bounds.left, bounds.right, bounds.bottom, bounds.top])
                    gdf.plot(ax=ax, facecolor='black', edgecolor='#38bdf8', linewidth=1.8, alpha=0.85)
                    ax.scatter([x_out], [y_out], color='red', marker='X', s=110, label='Aforo Original')
                    ax.scatter([x_snapped], [y_snapped], color='#eab308', marker='o', s=95, label='Punto de Cierre (Snap)')
                    ax.set_title("Cuenca Delimitada (Modelo D8 Estricto)", fontsize=12, fontweight='bold')
                    ax.legend(loc='upper right', fontsize=9)
                    fig.colorbar(im, label="Elevación (msnm)")
                    st.pyplot(fig)

                except Exception as e:
                    st.error(f"Error durante el procesamiento hidrológico: {e}")
    else:
        st.warning("Configure el DEM y el punto de aforo primero.")

elif opcion_menu == "4. Parametros y Hipsometria":
    if 'cuenca_generada' in st.session_state and st.session_state.cuenca_generada:
        st.subheader("Analisis Morfometrico y Curva Hipsometrica")
        
        with rasterio.open(st.session_state.dem_path) as src_dem:
            dem_raw = src_dem.read(1)
            nodata = src_dem.nodata

        basin_mask = st.session_state.basin_mask
        elevations = dem_raw[basin_mask]
        if nodata is not None:
            elevations = elevations[elevations != nodata]

        if len(elevations) > 0:
            elev_max = float(np.max(elevations))
            elev_min = float(np.min(elevations))
            elev_media = float(np.mean(elevations))
            
            # Curva Hipsometrica
            hist, bin_edges = np.histogram(elevations, bins=50)
            cumulative_area = np.cumsum(hist[::-1])[::-1]
            total_pixels = len(elevations)
            
            # Celda area en km2
            transform = st.session_state.transform
            pixel_width = abs(transform[0])
            pixel_height = abs(transform[4])
            is_geo = "4326" in st.session_state.selected_epsg
            
            if is_geo:
                pixel_area_km2 = (pixel_width * 111.32) * (pixel_height * 111.32)
            else:
                pixel_area_km2 = (pixel_width * pixel_height) / 1_000_000

            total_area_km2 = total_pixels * pixel_area_km2
            area_cum_km2 = cumulative_area * pixel_area_km2
            porcentaje_area = (area_cum_km2 / total_area_km2) * 100
            altitudes = (bin_edges[:-1] + bin_edges[1:]) / 2

            col1, col2 = st.columns(2)
            with col1:
                st.markdown("#### Parametros Altitudinales")
                st.metric("Elevacion Maxima", f"{elev_max:.2f} msnm")
                st.metric("Elevacion Minima", f"{elev_min:.2f} msnm")
                st.metric("Elevacion Media", f"{elev_media:.2f} msnm")
                st.metric("Rango Altitudinal", f"{elev_max - elev_min:.2f} m")

            with col2:
                fig, ax = plt.subplots(figsize=(6, 5))
                ax.plot(porcentaje_area, altitudes, color='#2563eb', linewidth=2.5)
                ax.set_title("Curva Hipsometrica", fontweight='bold')
                ax.set_xlabel("Area Mayor a la Altitud (%)")
                ax.set_ylabel("Altitud (msnm)")
                ax.grid(True, linestyle='--', alpha=0.6)
                st.pyplot(fig)
        else:
            st.warning("No se encontraron datos validos de elevacion en la cuenca.")
    else:
        st.info("Debe ejecutar el modelamiento hidrologico primero (Paso 3).")

elif opcion_menu == "5. Exportar":
    if 'cuenca_generada' in st.session_state and st.session_state.cuenca_generada:
        output_geojson = os.path.join(os.getcwd(), "cuenca_delimitada.geojson")
        if os.path.exists(output_geojson):
            with open(output_geojson, "rb") as f:
                st.download_button(
                    label="Descargar Poligono de Cuenca Formato GeoJSON",
                    data=f,
                    file_name="geocuenca_delimitada.geojson",
                    mime="application/geo+json",
                    type="primary"
                )
    else:
        st.info("Aun no se ha generado ninguna cuenca para exportar.")