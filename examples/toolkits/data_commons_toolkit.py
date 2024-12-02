# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========
from camel.toolkits.data_commons_toolkit import DataCommonsToolkit

# Initialize the DataCommonsToolkit
dc_toolkit = DataCommonsToolkit()

# Example 1: Query Data Commons
geoId06_name_query = '''
SELECT ?name ?dcid 
WHERE {
    ?a typeOf Place .
    ?a name ?name .
    ?a dcid ("geoId/06" "geoId/21" "geoId/24") .
    ?a dcid ?dcid
}
'''
result = dc_toolkit.query_data_commons(geoId06_name_query)
print("Query Result:")
print(result)

'''
===============================================================================
Query Result:
[{'?name': 'Kentucky', '?dcid': 'geoId/21'}, 
 {'?name': 'California', '?dcid': 'geoId/06'}, 
 {'?name': 'Maryland', '?dcid': 'geoId/24'}]
===============================================================================
'''

# Example 2: Get Triples
dcids = ["geoId/06", "geoId/21", "geoId/24"]
triples = dc_toolkit.get_triples(dcids)
print("\nTriples for California, Kentucky, and Maryland:")
print(triples)

'''
===============================================================================
Triples for California, Kentucky, and Maryland:
{
    "geoId/06": [
        ("name", "California"),
        ("containedInPlace", "country/USA"),
        ...
    ],
    "geoId/21": [
        ("name", "Kentucky"),
        ("containedInPlace", "country/USA"),
        ...
    ],
    "geoId/24": [
        ("name", "Maryland"),
        ("containedInPlace", "country/USA"),
        ...
    ]
}
===============================================================================
'''

# Example 3: Get Statistical Time Series
place = "geoId/06"
stat_var = "Count_Person"
series = dc_toolkit.get_stat_time_series(place, stat_var)
print("\nPopulation Time Series for California:")
print(series)

'''
===============================================================================
Population Time Series for California:
{
    "2010": 37253956,
    "2011": 37594778,
    "2012": 37971427,
    ...
}
===============================================================================
'''

# Example 4: Get Property Values
dcids = ["geoId/06", "geoId/21", "geoId/24"]
prop = "containedInPlace"
values = dc_toolkit.get_property_values(dcids, prop)
print("\nContained In Place for California, Kentucky, and Maryland:")
print(values)

'''
===============================================================================
Contained In Place for California, Kentucky, and Maryland:
{
    "geoId/06": ["country/USA"],
    "geoId/21": ["country/USA"],
    "geoId/24": ["country/USA"]
}
===============================================================================
'''

# Example 5: Get Statistical Value
place = "geoId/06"
stat_var = "Count_Person"
date = "2021"
value = dc_toolkit.get_stat_value(place, stat_var, date)
print("\nPopulation of California in 2021:")
print(value)

'''
===============================================================================
Population of California in 2021:
39237836
===============================================================================
'''
