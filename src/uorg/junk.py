import arcgis
import pandas as pd
import psycopg2
import sqlalchemy
from arcgis.features import GeoAccessor, GeoSeriesAccessor
from shapely import wkt
from sqlalchemy import create_engine

engine = create_engine('postgresql+psycopg2://agrc:agrc@opensgid.agrc.utah.gov:5432/opensgid')
db_conn = engine.connect()
df = pd.read_sql_table('county_boundaries', db_conn, schema='boundaries')
geoms = pd.read_sql('SELECT ST_AsText(shape) from boundaries.county_boundaries', db_conn)

shape = wkt.loads(geoms.iloc[0, 0])

arcgis.geometry.Geometry(shape)

# df['SHAPE'] = geoms.apply(lambda series: wkt.loads(series['st_astext']), axis=1)
# df.drop(columns='shape', inplace=True)
# pd.DataFrame.spatial.from_df(df, geometry_column='SHAPE')
