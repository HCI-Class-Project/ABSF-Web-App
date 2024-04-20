import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from streamlit_folium import folium_static
import folium
from SPARQLWrapper import SPARQLWrapper, JSON
import requests
import openmeteo_requests
import requests_cache
from retry_requests import retry
import wikidata.client as wd

api_key = "18c47b661bmshc3d19b2803dc6bfp147f5ejsn896964c2cb32"
api_host = "wft-geo-db.p.rapidapi.com"
headers = {
    "X-RapidAPI-Key": api_key,
    "X-RapidAPI-Host": api_host
}
cache_session = requests_cache.CachedSession('.cache', expire_after=-1)
retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
openmeteo = openmeteo_requests.Client(session=retry_session)

st.title("All About South Florida Web App")
st.header("Streamlit, GeoDB Cities API, Open-Meteo API, and Wikidata SPARQL Query")

st.divider()

tourist_attractions, graph_weather, raw_weather = st.tabs([
"Tourist Attractions",
"Graphical Weather Data",
"Raw Weather Data"
])

text_input_entered = False

@st.cache_data
def get_wpb_weather_data():
    # using lat and long of West Palm Beach
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": 26.7153,
        "longitude": -80.0534,
        "start_date": "1970-01-01",
        "end_date": "2020-01-01",
        "daily": ["temperature_2m_max", "temperature_2m_min", "temperature_2m_mean"],
        "temperature_unit": "fahrenheit",
        "wind_speed_unit": "mph",
        "precipitation_unit": "inch",
        "timezone": "America/New_York"
    }
    responses = openmeteo.weather_api(url, params=params)
    return responses


@st.cache_data
def get_ftlaudy_weather_data():
    # using lat and long of Fort Lauderdale
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": 26.1223,
        "longitude": -80.1434,
        "start_date": "1970-01-01",
        "end_date": "2020-01-01",
        "daily": ["temperature_2m_max", "temperature_2m_min", "temperature_2m_mean"],
        "temperature_unit": "fahrenheit",
        "wind_speed_unit": "mph",
        "precipitation_unit": "inch",
        "timezone": "America/New_York"
    }
    responses = openmeteo.weather_api(url, params=params)
    return responses


@st.cache_data
def get_miami_weather_data():
    # using lat and long of City of Miami
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": 25.7743,
        "longitude": -80.1937,
        "start_date": "1970-01-01",
        "end_date": "2020-01-01",
        "daily": ["temperature_2m_max", "temperature_2m_min", "temperature_2m_mean"],
        "temperature_unit": "fahrenheit",
        "wind_speed_unit": "mph",
        "precipitation_unit": "inch",
        "timezone": "America/New_York"
    }
    responses = openmeteo.weather_api(url, params=params)
    return responses


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
    querystring = {"radius": "50", "distanceUnit": "MI"}
    south_fl_counties_dict = requests.get(south_fl_counties_url, params=querystring, headers=headers).json()
    return south_fl_counties_dict

# P31 instanceof, P279 subclass, Q570116 tourist attraction
# P625 coordinate location, P131 located in admin. division
# Q695411 Palm Beach (town), Q986329 Jupiter (Town), Q29422 Boca Raton (City)

with tourist_attractions:
    south_fl_counties_dict = get_south_fl_counties()
    south_fl_counties_name = [county['name'] for county in south_fl_counties_dict['data']
                              if county['name'] != 'County Club Acres']
    selected_county = st.selectbox('Select a county', [""] + south_fl_counties_name,
                                   key="county_select_tourist")

    if selected_county == 'Palm Beach County':
        st.info(f"Selected county: {selected_county}")
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
                    attractions_data.append({'name': attraction_name,
                                             'latitude': latitude, 'longitude': longitude})
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
        st.info(f"Selected county: {selected_county}")
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
                    attractions_data.append({'name': attraction_name,
                                             'latitude': latitude, 'longitude': longitude})
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
        st.info(f"Selected county: {selected_county}")
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
        st.info("Please select a county.")

with graph_weather:
    south_fl_counties_dict = get_south_fl_counties()
    south_fl_counties_name = [county['name'] for county in south_fl_counties_dict['data']
                              if county['name'] != 'County Club Acres']
    selected_county = st.selectbox('Select a county', [""] + south_fl_counties_name,
                                   key="county_select_weather")

    if selected_county:
        st.info(f"Selected county: {selected_county}")
        start_date_graph_input = st.text_input("Start Date (MM/YYYY)", key="start_date_graphical")
        st.info("Please select dates in MM/YYYY format ranging from 01/1970 to 01/2020.")
        end_date_graph_input = st.text_input("End Date (MM/YYYY)", key="end_date_graphical")

        if start_date_graph_input.strip() and end_date_graph_input.strip():
            text_input_entered = True
            start_date_graph_input = start_date_graph_input + '/01'
            end_date_graph_input = end_date_graph_input + '/01'

            try:
                start_date_graph = pd.to_datetime(start_date_graph_input, format="%m/%Y/%d")
                end_date_graph = pd.to_datetime(end_date_graph_input, format="%m/%Y/%d")

                if start_date_graph < pd.to_datetime('1970-01-01') or end_date_graph > pd.to_datetime('2020-01-01'):
                    raise ValueError("Dates should be within the range from 01/1970 to 01/2020.")
                elif (end_date_graph - start_date_graph).days < 58:
                    raise ValueError("End date must be at least 2 months greater than start date.")

                elif start_date_graph is not None and end_date_graph is not None:
                    if selected_county == 'Palm Beach County':
                        responses = get_wpb_weather_data()
                        response = responses[0]

                        daily = response.Daily()
                        daily_temperature_2m_max = daily.Variables(0).ValuesAsNumpy()
                        daily_temperature_2m_min = daily.Variables(1).ValuesAsNumpy()
                        daily_temperature_2m_mean = daily.Variables(2).ValuesAsNumpy()
                        daily_data = {"date": pd.date_range(
                            start=pd.to_datetime(daily.Time(), unit="s", utc=True),
                            end=pd.to_datetime(daily.TimeEnd(), unit="s", utc=True),
                            freq=pd.Timedelta(seconds=daily.Interval()),
                            inclusive="left"
                        )}
                        daily_data["temperature_2m_max"] = daily_temperature_2m_max
                        daily_data["temperature_2m_min"] = daily_temperature_2m_min
                        daily_data["temperature_2m_mean"] = daily_temperature_2m_mean
                        daily_dataframe = pd.DataFrame(data=daily_data)
                        daily_dataframe['date'] = pd.to_datetime(daily_dataframe['date'])
                        monthly_dataframe = daily_dataframe.resample('M', on='date').mean().reset_index()

                        monthly_dataframe['date'] = monthly_dataframe['date'].dt.tz_localize(None)
                        user_monthly_dataframe = monthly_dataframe[
                            (monthly_dataframe['date'] >= start_date_graph) & (monthly_dataframe['date'] <= end_date_graph)]

                        fig1_box = st.checkbox("Show Monthly Average Temperature", value=False)
                        if fig1_box:
                            st.subheader("Monthly Average Temperature in Fahrenheit")
                            fig1 = px.line(user_monthly_dataframe, x='date', y='temperature_2m_mean',
                                           title='Monthly Average Temperature Over Specified Data Range')
                            color = st.color_picker("Choose a color", "#081E3F")
                            fig1.update_traces(line_color=color)
                            fig1.update_layout(
                                xaxis_title='Date',
                                yaxis_title='Average Mean Temperature'
                            )
                            fig1.for_each_trace(lambda t: t.update(y=np.round(t.y, 2)))
                            st.plotly_chart(fig1)

                        fig2_box = st.checkbox("Show Average Maximum and Minimum Temperatures", value=False)
                        if fig2_box:
                            st.subheader("Average Maximum and Average Minimum Monthly Temperatures in Fahrenheit")
                            fig2 = go.Figure()

                            fig2.add_trace(go.Scatter(
                                x=user_monthly_dataframe['date'],
                                y=user_monthly_dataframe['temperature_2m_max'],
                                fill='tozeroy',
                                mode='none',
                                line=dict(color='rgba(255, 128, 0, 0.7)'),
                                fillcolor='rgba(255, 128, 0, 0.4)',
                                name='Average Maximum Temperature'
                            ))
                            fig2.update_traces(hoverlabel=dict(font=dict(color='white')))
                            fig2.add_trace(go.Scatter(
                                x=user_monthly_dataframe['date'],
                                y=user_monthly_dataframe['temperature_2m_min'],
                                fill='tozeroy',
                                mode='none',
                                line=dict(color='rgba(0, 100, 0, 0.7)'),
                                fillcolor='rgba(0, 100, 0, 0.7)',
                                name='Average Minimum Temperature'
                            ))
                            fig2.update_traces(hoverlabel=dict(font=dict(color='white')))
                            fig2.update_layout(
                                title='Average Maximum and Minimum Temperatures Over Specified Data Range',
                                xaxis_title='Date',
                                yaxis_title='Temperature (°F)',
                                yaxis_range=[50, 95]
                            )
                            fig2.for_each_trace(lambda t: t.update(y=np.round(t.y, 2)))
                            st.plotly_chart(fig2)
                    elif selected_county == 'Broward County':
                        responses = get_ftlaudy_weather_data()
                        response = responses[0]

                        daily = response.Daily()
                        daily_temperature_2m_max = daily.Variables(0).ValuesAsNumpy()
                        daily_temperature_2m_min = daily.Variables(1).ValuesAsNumpy()
                        daily_temperature_2m_mean = daily.Variables(2).ValuesAsNumpy()
                        daily_data = {"date": pd.date_range(
                            start=pd.to_datetime(daily.Time(), unit="s", utc=True),
                            end=pd.to_datetime(daily.TimeEnd(), unit="s", utc=True),
                            freq=pd.Timedelta(seconds=daily.Interval()),
                            inclusive="left"
                        )}
                        daily_data["temperature_2m_max"] = daily_temperature_2m_max
                        daily_data["temperature_2m_min"] = daily_temperature_2m_min
                        daily_data["temperature_2m_mean"] = daily_temperature_2m_mean
                        daily_dataframe = pd.DataFrame(data=daily_data)
                        daily_dataframe['date'] = pd.to_datetime(daily_dataframe['date'])
                        monthly_dataframe = daily_dataframe.resample('M', on='date').mean().reset_index()

                        monthly_dataframe['date'] = monthly_dataframe['date'].dt.tz_localize(None)
                        user_monthly_dataframe = monthly_dataframe[
                            (monthly_dataframe['date'] >= start_date_graph) & (monthly_dataframe['date'] <= end_date_graph)]

                        fig1_box = st.checkbox("Show Monthly Average Temperature", value=False)
                        if fig1_box:
                            st.subheader("Monthly Average Temperature in Fahrenheit")
                            fig1 = px.line(user_monthly_dataframe, x='date', y='temperature_2m_mean',
                                           title='Monthly Average Temperature Over Specified Data Range')
                            color = st.color_picker("Choose a color", "#081E3F")
                            fig1.update_traces(line_color=color)
                            fig1.update_layout(
                                xaxis_title='Date',
                                yaxis_title='Average Mean Temperature'
                            )
                            fig1.for_each_trace(lambda t: t.update(y=np.round(t.y, 2)))
                            st.plotly_chart(fig1)

                        fig2_box = st.checkbox("Show Average Maximum and Minimum Temperatures", value=False)
                        if fig2_box:
                            st.subheader("Average Maximum and Average Minimum Monthly Temperatures in Fahrenheit")
                            fig2 = go.Figure()

                            fig2.add_trace(go.Scatter(
                                x=user_monthly_dataframe['date'],
                                y=user_monthly_dataframe['temperature_2m_max'],
                                fill='tozeroy',
                                mode='none',
                                line=dict(color='rgba(255, 128, 0, 0.7)'),
                                fillcolor='rgba(255, 128, 0, 0.4)',
                                name='Average Maximum Temperature'
                            ))
                            fig2.update_traces(hoverlabel=dict(font=dict(color='white')))
                            fig2.add_trace(go.Scatter(
                                x=user_monthly_dataframe['date'],
                                y=user_monthly_dataframe['temperature_2m_min'],
                                fill='tozeroy',
                                mode='none',
                                line=dict(color='rgba(0, 100, 0, 0.7)'),
                                fillcolor='rgba(0, 100, 0, 0.7)',
                                name='Average Minimum Temperature'
                            ))
                            fig2.update_traces(hoverlabel=dict(font=dict(color='white')))
                            fig2.update_layout(
                                title='Average Maximum and Minimum Temperatures Over Specified Data Range',
                                xaxis_title='Date',
                                yaxis_title='Temperature (°F)',
                                yaxis_range=[50, 95]
                            )
                            fig2.for_each_trace(lambda t: t.update(y=np.round(t.y, 2)))
                            st.plotly_chart(fig2)
                    elif selected_county == 'Miami-Dade County':
                        responses = get_miami_weather_data()
                        response = responses[0]

                        daily = response.Daily()
                        daily_temperature_2m_max = daily.Variables(0).ValuesAsNumpy()
                        daily_temperature_2m_min = daily.Variables(1).ValuesAsNumpy()
                        daily_temperature_2m_mean = daily.Variables(2).ValuesAsNumpy()
                        daily_data = {"date": pd.date_range(
                            start=pd.to_datetime(daily.Time(), unit="s", utc=True),
                            end=pd.to_datetime(daily.TimeEnd(), unit="s", utc=True),
                            freq=pd.Timedelta(seconds=daily.Interval()),
                            inclusive="left"
                        )}
                        daily_data["temperature_2m_max"] = daily_temperature_2m_max
                        daily_data["temperature_2m_min"] = daily_temperature_2m_min
                        daily_data["temperature_2m_mean"] = daily_temperature_2m_mean
                        daily_dataframe = pd.DataFrame(data=daily_data)
                        daily_dataframe['date'] = pd.to_datetime(daily_dataframe['date'])
                        monthly_dataframe = daily_dataframe.resample('M', on='date').mean().reset_index()

                        monthly_dataframe['date'] = monthly_dataframe['date'].dt.tz_localize(None)
                        user_monthly_dataframe = monthly_dataframe[
                            (monthly_dataframe['date'] >= start_date_graph) & (monthly_dataframe['date'] <= end_date_graph)]

                        fig1_box = st.checkbox("Show Monthly Average Temperature", value=False)
                        if fig1_box:
                            st.subheader("Monthly Average Temperature in Fahrenheit")
                            fig1 = px.line(user_monthly_dataframe, x='date', y='temperature_2m_mean',
                                           title='Monthly Average Temperature Over Specified Data Range')
                            color = st.color_picker("Choose a color", "#081E3F")
                            fig1.update_traces(line_color=color)
                            fig1.update_layout(
                                xaxis_title='Date',
                                yaxis_title='Average Mean Temperature'
                            )
                            fig1.for_each_trace(lambda t: t.update(y=np.round(t.y, 2)))
                            st.plotly_chart(fig1)

                        fig2_box = st.checkbox("Show Average Maximum and Minimum Temperatures", value=False)
                        if fig2_box:
                            st.subheader("Average Maximum and Average Minimum Monthly Temperatures in Fahrenheit")
                            fig2 = go.Figure()

                            fig2.add_trace(go.Scatter(
                                x=user_monthly_dataframe['date'],
                                y=user_monthly_dataframe['temperature_2m_max'],
                                fill='tozeroy',
                                mode='none',
                                line=dict(color='rgba(255, 128, 0, 0.7)'),
                                fillcolor='rgba(255, 128, 0, 0.4)',
                                name='Average Maximum Temperature'
                            ))
                            fig2.update_traces(hoverlabel=dict(font=dict(color='white')))
                            fig2.add_trace(go.Scatter(
                                x=user_monthly_dataframe['date'],
                                y=user_monthly_dataframe['temperature_2m_min'],
                                fill='tozeroy',
                                mode='none',
                                line=dict(color='rgba(0, 100, 0, 0.7)'),
                                fillcolor='rgba(0, 100, 0, 0.7)',
                                name='Average Minimum Temperature'
                            ))
                            fig2.update_traces(hoverlabel=dict(font=dict(color='white')))
                            fig2.update_layout(
                                title='Average Maximum and Minimum Temperatures Specified Over Data Range',
                                xaxis_title='Date',
                                yaxis_title='Temperature (°F)',
                                yaxis_range=[50, 95]
                            )
                            fig2.for_each_trace(lambda t: t.update(y=np.round(t.y, 2)))
                            st.plotly_chart(fig2)
                    else:
                        st.error("Please select a county.")
            except ValueError as e:
                if "format" in str(e):
                    st.error("Invalid date format. Please enter valid dates in MM/YYYY format.")
                elif "End date must be greater than start date." in str(e):
                    st.error("End date must be at least 2 months greater than start date.")
                else:
                    st.error(str(e))
with raw_weather:
    south_fl_counties_dict = get_south_fl_counties()
    south_fl_counties_name = [county['name'] for county in south_fl_counties_dict['data']
                              if county['name'] != 'County Club Acres']
    selected_county = st.selectbox('Select a county', [""] + south_fl_counties_name,
                                   key="county_raw_weather")

    if selected_county:
        st.info(f"Selected county: {selected_county}")
        start_date_raw_input = st.text_input("Start Date (MM/YYYY)", key="start_date_raw")
        st.info("Please select dates in MM/YYYY format ranging from 01/1970 to 01/2020.")
        end_date_raw_input = st.text_input("End Date (MM/YYYY)", key="end_date_raw")

        if start_date_raw_input.strip() and end_date_raw_input.strip():
            text_input_entered = True
            start_date_raw_input = start_date_raw_input + '/01'
            end_date_raw_input = end_date_raw_input + '/01'

            try:
                start_date_raw = pd.to_datetime(start_date_raw_input, format="%m/%Y/%d")
                end_date_raw = pd.to_datetime(end_date_raw_input, format="%m/%Y/%d")

                if start_date_raw < pd.to_datetime('1970-01-01') or end_date_raw > pd.to_datetime('2020-01-01'):
                    raise ValueError("Dates should be within the range from 01/1970 to 01/2020.")
                elif (end_date_raw - start_date_raw).days < 58:
                    raise ValueError("End date must be at least 2 months greater than start date.")

                elif start_date_raw is not None and end_date_raw is not None:
                    if selected_county == 'Palm Beach County':
                        responses = get_wpb_weather_data()
                        response = responses[0]

                        daily = response.Daily()
                        daily_temperature_2m_max = daily.Variables(0).ValuesAsNumpy()
                        daily_temperature_2m_min = daily.Variables(1).ValuesAsNumpy()
                        daily_temperature_2m_mean = daily.Variables(2).ValuesAsNumpy()
                        daily_data = {"date": pd.date_range(
                            start=pd.to_datetime(daily.Time(), unit="s", utc=True),
                            end=pd.to_datetime(daily.TimeEnd(), unit="s", utc=True),
                            freq=pd.Timedelta(seconds=daily.Interval()),
                            inclusive="left"
                        )}
                        daily_data["temperature_2m_max"] = daily_temperature_2m_max
                        daily_data["temperature_2m_min"] = daily_temperature_2m_min
                        daily_data["temperature_2m_mean"] = daily_temperature_2m_mean
                        daily_dataframe = pd.DataFrame(data=daily_data)
                        daily_dataframe['date'] = pd.to_datetime(daily_dataframe['date'])
                        monthly_dataframe = daily_dataframe.resample('M', on='date').mean().reset_index()
                        monthly_dataframe['date'] = monthly_dataframe['date'].dt.tz_localize(None)

                        monthly_dataframe = monthly_dataframe.rename(columns={
                            'date': 'Date',
                            'temperature_2m_max': 'Average Max Temperature',
                            'temperature_2m_min': 'Average Min Temperature',
                            'temperature_2m_mean': 'Average Mean Temperature',
                        })

                        st.subheader("Raw Monthly Weather Data")
                        filtered_monthly_data = monthly_dataframe[
                            (monthly_dataframe['Date'] >= start_date_raw) & (monthly_dataframe['Date'] <= end_date_raw)]
                        filtered_monthly_data = filtered_monthly_data.round({'Average Max Temperature': 2,
                                                                             'Average Min Temperature': 2,
                                                                             'Average Mean Temperature': 2})
                        st.write(filtered_monthly_data)

                    elif selected_county == 'Broward County':
                        responses = get_ftlaudy_weather_data()
                        response = responses[0]

                        daily = response.Daily()
                        daily_temperature_2m_max = daily.Variables(0).ValuesAsNumpy()
                        daily_temperature_2m_min = daily.Variables(1).ValuesAsNumpy()
                        daily_temperature_2m_mean = daily.Variables(2).ValuesAsNumpy()
                        daily_data = {"date": pd.date_range(
                            start=pd.to_datetime(daily.Time(), unit="s", utc=True),
                            end=pd.to_datetime(daily.TimeEnd(), unit="s", utc=True),
                            freq=pd.Timedelta(seconds=daily.Interval()),
                            inclusive="left"
                        )}
                        daily_data["temperature_2m_max"] = daily_temperature_2m_max
                        daily_data["temperature_2m_min"] = daily_temperature_2m_min
                        daily_data["temperature_2m_mean"] = daily_temperature_2m_mean
                        daily_dataframe = pd.DataFrame(data=daily_data)
                        daily_dataframe['date'] = pd.to_datetime(daily_dataframe['date'])
                        monthly_dataframe = daily_dataframe.resample('M', on='date').mean().reset_index()
                        monthly_dataframe['date'] = monthly_dataframe['date'].dt.tz_localize(None)

                        monthly_dataframe = monthly_dataframe.rename(columns={
                            'date': 'Date',
                            'temperature_2m_max': 'Average Max Temperature',
                            'temperature_2m_min': 'Average Min Temperature',
                            'temperature_2m_mean': 'Average Mean Temperature'
                        })

                        st.subheader("Raw Monthly Weather Data")
                        filtered_monthly_data = monthly_dataframe[
                            (monthly_dataframe['Date'] >= start_date_raw) & (monthly_dataframe['Date'] <= end_date_raw)]
                        filtered_monthly_data = filtered_monthly_data.round({'Average Max Temperature': 2,
                                                                             'Average Min Temperature': 2,
                                                                             'Average Mean Temperature': 2})
                        st.write(filtered_monthly_data)

                    elif selected_county == 'Miami-Dade County':
                        responses = get_miami_weather_data()
                        response = responses[0]

                        daily = response.Daily()
                        daily_temperature_2m_max = daily.Variables(0).ValuesAsNumpy()
                        daily_temperature_2m_min = daily.Variables(1).ValuesAsNumpy()
                        daily_temperature_2m_mean = daily.Variables(2).ValuesAsNumpy()
                        daily_data = {"date": pd.date_range(
                            start=pd.to_datetime(daily.Time(), unit="s", utc=True),
                            end=pd.to_datetime(daily.TimeEnd(), unit="s", utc=True),
                            freq=pd.Timedelta(seconds=daily.Interval()),
                            inclusive="left"
                        )}
                        daily_data["temperature_2m_max"] = daily_temperature_2m_max
                        daily_data["temperature_2m_min"] = daily_temperature_2m_min
                        daily_data["temperature_2m_mean"] = daily_temperature_2m_mean
                        daily_dataframe = pd.DataFrame(data=daily_data)
                        daily_dataframe['date'] = pd.to_datetime(daily_dataframe['date'])
                        monthly_dataframe = daily_dataframe.resample('M', on='date').mean().reset_index()
                        monthly_dataframe['date'] = monthly_dataframe['date'].dt.tz_localize(None)

                        monthly_dataframe = monthly_dataframe.rename(columns={
                            'date': 'Date',
                            'temperature_2m_max': 'Average Max Temperature',
                            'temperature_2m_min': 'Average Min Temperature',
                            'temperature_2m_mean': 'Average Mean Temperature'
                        })

                        st.subheader("Raw Monthly Weather Data")
                        filtered_monthly_data = monthly_dataframe[
                            (monthly_dataframe['Date'] >= start_date_raw) & (monthly_dataframe['Date'] <= end_date_raw)]
                        filtered_monthly_data = filtered_monthly_data.round({'Average Max Temperature': 2,
                                                                             'Average Min Temperature': 2,
                                                                             'Average Mean Temperature': 2})
                        st.write(filtered_monthly_data)

                    else:
                        st.info("Please select a county.")
            except ValueError as e:
                if "format" in str(e):
                    st.error("Invalid date format. Please enter valid dates in MM/YYYY format.")
                elif "End date must be greater than start date." in str(e):
                    st.error("End date must be at least 2 months greater than start date.")
                else:
                    st.error(str(e))


if text_input_entered:
    st.sidebar.title("Hey you!")
    rate_answer = st.sidebar.radio("Would you like to rate your experience?", ["Yes", "No"], index=None)
    if rate_answer == "Yes":
        rating = st.sidebar.slider('Rate your experience with our web app!', 1, 5, 3)
        if rating:
            submit_button = st.sidebar.button("Submit Rating")
            if submit_button:
                st.sidebar.success("Thank you for your feedback! Your rating: {}.".format(rating))
    elif rate_answer == "No":
        st.sidebar.info("Thank you for your time!")
