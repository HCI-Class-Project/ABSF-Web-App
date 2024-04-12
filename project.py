import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from streamlit_folium import folium_static
import folium
from SPARQLWrapper import SPARQLWrapper, JSON
import requests
import wikidata.client as wd
api_key = "18c47b661bmshc3d19b2803dc6bfp147f5ejsn896964c2cb32"
api_host = "wft-geo-db.p.rapidapi.com"
headers = {
    "X-RapidAPI-Key": api_key,
    "X-RapidAPI-Host": api_host
}

st.title("All About South Florida Web App")
st.header("Streamlit, GeoDB Cities API, and Wikidata SPARQL Query")

@st.cache_data
def map_creator(attractions):
    latitudes = [attraction['latitude'] for attraction in attractions]
    longitudes = [attraction['longitude'] for attraction in attractions]

    min_lat, max_lat = min(latitudes), max(latitudes)
    min_lon, max_lon = min(longitudes), max(longitudes)
    center_lat = (min_lat + max_lat) / 2
    center_lon = (min_lon + max_lon) / 2

    m = folium.Map(location=[center_lat, center_lon], zoom_start=9)


    for attraction in attractions:
        folium.Marker(
            location=[attraction['latitude'], attraction['longitude']],
            popup=attraction['name'],
            tooltip=attraction['name']
        ).add_to(m)

    return m
@st.cache_data
def get_south_fl_counties():
    south_fl_counties_url = "https://wft-geo-db.p.rapidapi.com/v1/geo/locations/26.1901-80.3659/nearbyDivisions"
    querystring = {"radius":"50","distanceUnit":"MI"}
    south_fl_counties_dict = requests.get(south_fl_counties_url, params=querystring, headers=headers).json()
    return south_fl_counties_dict

south_fl_counties_dict = get_south_fl_counties()
south_fl_counties_name = [county['name'] for county in south_fl_counties_dict['data'] if county['name'] != 'County Club Acres']
selected_county = st.selectbox('Select a county', south_fl_counties_name)
st.info(f"Selected county: {selected_county}")



# P31 instanceof, P279 subclass, Q570116 tourist attraction
# P625 coordinate location, P131 located in admin. division
# Q695411 Palm Beach (town), Q986329 Jupiter (Town), Q29422 Boca Raton (City)
if selected_county == 'Palm Beach County':
    sparql_query = """
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX wd: <http://www.wikidata.org/entity/>
    PREFIX wdt: <http://www.wikidata.org/prop/direct/>
    
    SELECT DISTINCT ?attraction ?attractionLabel ?gps 
    WHERE {
        ?attraction (wdt:P31/wdt:P279*) wd:Q570116;
            wdt:P625 ?gps;
            rdfs:label ?attractionLabel.
            
        {?attraction wdt:P131 wd:Q695411}
        UNION
        {?attraction wdt:P131 wd:Q986329}
        UNION
        {?attraction wdt:P131 wd:Q29422}
        
        FILTER(LANG(?attractionLabel) = "en")
    }
    """
    sparql = SPARQLWrapper("https://query.wikidata.org/sparql")
    sparql.setQuery(sparql_query)
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()

    if 'results' in results and 'bindings' in results['results']:
        attractions = results['results']['bindings']
        st.subheader("Tourist Attractions in Palm Beach County")

        attractions_data = []
        for attraction in attractions:
            attraction_name = attraction['attractionLabel']['value']
            gps_coordinates = attraction['gps']['value']
            if gps_coordinates.startswith("Point(") and gps_coordinates.endswith(")"):
                gps_coordinates = gps_coordinates[6:-1]
                latitude, longitude = map(float, gps_coordinates.split(" ")[::-1])
                attractions_data.append({'name': attraction_name, 'latitude': latitude, 'longitude': longitude})
                st.write(f"- **{attraction_name}**: ({latitude}, {longitude})")
            else:
                st.error(f"Invalid GPS coordinates format for attraction '{attraction_name}'.")

        attractions_table = pd.DataFrame(attractions_data)
        st.write(attractions_table)
        map = map_creator(attractions_data)
        st.subheader("Tourist Attractions Map")
        folium_static(map)
    else:
        st.error("Failed to retrieve tourist attractions. Please try again later.")


elif selected_county == 'Broward County':
# Q494624 Broward County, Q988906 Coconut Creek (city), Q505557 Coral Springs (city)
# Q671458 Pompano Beach (city), Q165972 Fort Lauderdale (city), Q985438 Davie (town)
    sparql_query = """
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX wd: <http://www.wikidata.org/entity/>
    PREFIX wdt: <http://www.wikidata.org/prop/direct/>

    SELECT DISTINCT ?attraction ?attractionLabel ?gps 
    WHERE {
        ?attraction (wdt:P31/wdt:P279*) wd:Q570116;
            wdt:P625 ?gps;
            rdfs:label ?attractionLabel.

        {?attraction wdt:P131 wd:Q494624}
        UNION
        {?attraction wdt:P131 wd:Q988906}
        UNION
        {?attraction wdt:P131 wd:Q505557}
        UNION
        {?attraction wdt:P131 wd:Q671458}
        UNION
        {?attraction wdt:P131 wd:Q165972}
        UNION
        {?attraction wdt:P131 wd:Q985438}

        FILTER(LANG(?attractionLabel) = "en")
    }
    """
    sparql = SPARQLWrapper("https://query.wikidata.org/sparql")
    sparql.setQuery(sparql_query)
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()

    if 'results' in results and 'bindings' in results['results']:
        attractions = results['results']['bindings']
        st.subheader("Tourist Attractions in Broward County")

        attractions_data = []
        for attraction in attractions:
            attraction_name = attraction['attractionLabel']['value']
            gps_coordinates = attraction['gps']['value']
            if gps_coordinates.startswith("Point(") and gps_coordinates.endswith(")"):
                gps_coordinates = gps_coordinates[6:-1]
                latitude, longitude = map(float, gps_coordinates.split(" ")[::-1])
                attractions_data.append({'name': attraction_name, 'latitude': latitude, 'longitude': longitude})
                st.write(f"- **{attraction_name}**: ({latitude}, {longitude})")
            else:
                st.error(f"Invalid GPS coordinates format for attraction '{attraction_name}'.")

        attractions_table = pd.DataFrame(attractions_data)
        st.write(attractions_table)
        map = map_creator(attractions_data)
        st.subheader("Tourist Attractions Map")
        folium_static(map)
    else:
        st.error("Failed to retrieve tourist attractions. Please try again later.")


elif selected_county == 'Miami-Dade County':
# Q468557 Miami-Dade County, Q988909 North Miami Beach (city), Q980428 North Miami (city)
# Q8652 Miami (city), Q201516 Miami Beach (city), Q280557 Homestead (city), Q8040258 Wynwood (neighborhood)
    sparql_query = """
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX wd: <http://www.wikidata.org/entity/>
    PREFIX wdt: <http://www.wikidata.org/prop/direct/>
    
    SELECT DISTINCT ?attraction ?attractionLabel ?gps 
    
    WHERE {
        ?attraction (wdt:P31/wdt:P279*) wd:Q570116;
            wdt:P625 ?gps;
            rdfs:label ?attractionLabel.
     
        {?attraction wdt:P131 wd:Q468557}
        UNION
        {?attraction wdt:P131 wd:Q988909}
        UNION
        {?attraction wdt:P131 wd:Q980428}
        UNION
        {?attraction wdt:P131 wd:Q8652}
        UNION
        {?attraction wdt:P131 wd:Q201516}
        UNION
        {?attraction wdt:P131 wd:Q280557}
        UNION
        {?attraction wdt:P131 wd:Q8040258}
        
                
        FILTER(LANG(?attractionLabel) = "en")
    }
    """
    sparql = SPARQLWrapper("https://query.wikidata.org/sparql")
    sparql.setQuery(sparql_query)
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()

    if 'results' in results and 'bindings' in results['results']:
        attractions = results['results']['bindings']
        st.subheader("Tourist Attractions in Miami-Dade County")

        attractions_data = []
        for attraction in attractions:
            attraction_name = attraction['attractionLabel']['value']
            gps_coordinates = attraction['gps']['value']
            if gps_coordinates.startswith("Point(") and gps_coordinates.endswith(")"):
                gps_coordinates = gps_coordinates[6:-1]
                latitude, longitude = map(float, gps_coordinates.split(" ")[::-1])
                attractions_data.append({'name': attraction_name, 'latitude': latitude, 'longitude': longitude})
                st.write(f"- **{attraction_name}**: ({latitude}, {longitude})")
            else:
                st.error(f"Invalid GPS coordinates format for attraction '{attraction_name}'.")

        attractions_table = pd.DataFrame(attractions_data)
        st.write(attractions_table)
        map = map_creator(attractions_data)
        st.subheader("Tourist Attractions Map")
        folium_static(map)
    else:
        st.error("Failed to retrieve tourist attractions. Please try again later.")
else:
    st.error("Invalid county. Please try again later.")
